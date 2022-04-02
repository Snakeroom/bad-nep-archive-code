import datetime
import logging
import os.path
from functools import lru_cache

import httpx
from b2sdk.exception import TooManyRequests
from placedump.common import get_b2_api, get_redis
from placedump.model import Pixel, sm
from placedump.tasks import app
from pottery import Redlock
from sqlalchemy.dialects.postgresql import insert

log = logging.getLogger(__name__)
CONTRACT_DOWNLOAD_LOCK = 60


def fetch_http(url: str) -> bytes:
    req = httpx.get(url, follow_redirects=True)
    req.raise_for_status()
    content = req.content

    return content


@lru_cache
def get_bucket(name: str):
    b2 = get_b2_api()
    return b2.get_bucket_by_name(name)


@app.task(
    autoretry_for=(TooManyRequests,),
    retry_backoff=2,
)
def download_url(url: str):
    redis = get_redis()
    bucket = get_bucket("erin-reddit-afd2022")

    upload_lock = Redlock(
        key=f"download:{url}",
        masters={redis},
        auto_release_time=CONTRACT_DOWNLOAD_LOCK,
    )
    data = fetch_http(url)

    # Upload the file one worker at a time.
    with upload_lock:
        filename = url.replace("https://", "")
        log.info(f"{url}, {len(data)} bytes.")
        bucket.upload_bytes(data, filename)


@app.task()
def update_pixel(board_id: int, x: int, y: int, pixel_data: dict):
    user = pixel_data["userInfo"]["username"]
    timestamp = float(pixel_data["lastModifiedTimestamp"]) / 1000.0

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
