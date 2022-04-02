import datetime
import json
import logging
import os.path
from functools import lru_cache
from io import BytesIO

import httpx
import numpy as np
from async_timeout import timeout
from b2sdk.exception import TooManyRequests
from gql import gql
from PIL import Image
from placedump.common import ctx_redis, get_b2_api, get_gql_client, get_redis
from placedump.model import Pixel, sm
from placedump.tasks import app
from pottery import Redlock
from sqlalchemy.dialects.postgresql import insert

log = logging.getLogger(__name__)
CONTRACT_DOWNLOAD_LOCK = 60

query_get_pixel = gql(
    """
  mutation pixelHistory($input: ActInput!) {
    act(input: $input) {
      data {
        ... on BasicMessage {
          id
          data {
            ... on GetTileHistoryResponseMessageData {
              lastModifiedTimestamp
              userInfo {
                userID
                username
              }
            }
          }
        }
      }
    }
  }
 """
)


def fetch_http(url: str) -> bytes:
    req = httpx.get(url, follow_redirects=True)
    req.raise_for_status()
    content = req.content

    return content


@app.task()
def get_non_transparent(board, content: bytes):
    # https://stackoverflow.com/questions/60051941/find-the-coordinates-in-an-image-where-a-specified-colour-is-detected
    f_data = BytesIO(content)

    # parse
    img = Image.open(f_data).convert("RGBA")
    np_img = np.array(img)

    Y, X = np.where(np.all(np_img != (0, 0, 0, 0), axis=2))

    changed = list(np.column_stack((X, Y)))
    if len(changed) > 250:
        return []

    # queue all pixels
    with ctx_redis() as redis:
        for cords in changed:
            x, y = cords
            x = int(x)
            y = int(y)
            redis.sadd(
                "queue:pixels",
                json.dumps(
                    {
                        "x": x,
                        "y": y,
                        "board": board,
                    }
                ),
            )

    return changed


@lru_cache
def get_bucket(name: str):
    b2 = get_b2_api()
    return b2.get_bucket_by_name(name)


@app.task(
    autoretry_for=(TooManyRequests,),
    retry_backoff=2,
)
def download_url(board: int, url: str):
    bucket = get_bucket("erin-reddit-afd2022")

    with ctx_redis() as redis:
        upload_lock = Redlock(
            key=f"download:{url}", masters={redis}, auto_release_time=60
        )

        # Upload the file one worker at a time.
        with upload_lock:
            data = fetch_http(url)
            filename = url.replace("https://", "")
            log.info(f"{url}, {len(data)} bytes.")
            bucket.upload_bytes(data, filename)

    # Also kick off the image parsing loop.
    get_non_transparent.delay(board, data)


@app.task()
def update_pixel(board_id: int, x: int, y: int, pixel_data: dict):
    try:
        user = pixel_data["userInfo"]["username"]
        timestamp = float(pixel_data["lastModifiedTimestamp"]) / 1000.0
    except (TypeError, KeyError):
        return

    timestamp = datetime.datetime.fromtimestamp(timestamp)

    # Create the DB entry.
    with sm() as db:
        db.execute(
            insert(Pixel)
            .values(
                board_id=board_id,
                x=x,
                y=y,
                user=user,
                modified=timestamp,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    "x",
                    "y",
                    "modified",
                ]
            )
        )
        db.commit()


@app.task
def get_pixels(pixels, push: bool = True):
    gql_client = get_gql_client()
    variables = {}
    pixels_index = {}

    for index, pixel in enumerate(pixels):
        x, y = pixel
        x = int(x)
        y = int(y)

        variables["input" + str(index + 1)] = {
            "actionName": "r/replace:get_tile_history",
            "PixelMessageData": {
                "canvasIndex": 0,
                "colorIndex": 0,
                "coordinate": {"x": x, "y": y},
            },
        }
        pixels_index["input" + str(index + 1)] = (x, y)

    result = gql_client.execute(query_get_pixel_8x, variable_values=variables)

    for input_name, gql_res in result.items():
        x, y = pixels_index[input_name]
        pixel = gql_res["data"][0]["data"]

        update_pixel.apply_async(
            kwargs=dict(
                board_id=1,
                x=x,
                y=y,
                pixel_data=pixel,
            ),
            priority=5,
        )


@app.task
def get_pixel(x: int, y: int, push: bool = True):
    gql_client = get_gql_client()

    variables = {
        "input": {
            "actionName": "r/replace:get_tile_history",
            "PixelMessageData": {
                "canvasIndex": 0,
                "colorIndex": 0,
                "coordinate": {"x": x, "y": y},
            },
        }
    }

    result = gql_client.execute(query_get_pixel, variable_values=variables)

    pixel = result["act"]["data"][0]["data"]
    result = dict(
        board_id=1,
        x=x,
        y=y,
        pixel_data=pixel,
    )
    if push:
        update_pixel.apply_async(
            kwargs=result,
            priority=5,
        )

    return result
