import asyncio
import functools
import json
import logging
from concurrent.futures import ProcessPoolExecutor
from io import BytesIO

import aiohttp
import aioredis
import async_timeout
import numpy as np
import requests
from gql import Client, gql
from gql.transport.websockets import WebsocketsTransport
from PIL import Image

from placedump.common import ctx_aioredis, get_token, headers
from placedump.tasks.pixels import update_pixel

# logging.basicConfig(level=logging.DEBUG)
running = True
tasks = []
payload_queue = asyncio.Queue()
pixel_queue = asyncio.Queue()
pool = ProcessPoolExecutor(max_workers=8)


def get_non_transparent(url):
    # https://stackoverflow.com/questions/60051941/find-the-coordinates-in-an-image-where-a-specified-colour-is-detected

    # fetch
    req = requests.get(url)
    f_data = BytesIO(req.content)

    # parse
    img = Image.open(f_data).convert("RGBA")
    np_img = np.array(img)

    Y, X = np.where(np.all(np_img != (0, 0, 0, 0), axis=2))

    changed = list(np.column_stack((X, Y)))
    if len(changed) > 250:
        return []

    return changed


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

query_get_pixel_8x = gql(
    """
  mutation pixelHistory($input1: ActInput!, $input2: ActInput!, $input3: ActInput!, $input4: ActInput!, $input5: ActInput!, $input6: ActInput!) {
    input1: act(input: $input1) {
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
    input2: act(input: $input2) {
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
    input3: act(input: $input3) {
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
    input4: act(input: $input4) {
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
    input5: act(input: $input5) {
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
    input6: act(input: $input6) {
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


async def parser(session: aiohttp.ClientSession):
    while running or payload_queue.qsize() > 0:
        while payload_queue.qsize() == 0:
            await asyncio.sleep(0.25)
        payload = await payload_queue.get()
        payload_queue.task_done()

        try:
            url = payload["payload"]["data"]["subscribe"]["data"]["name"]
        except KeyError:
            print("invalid payload", payload)
            continue

        for pixel in await asyncio.get_event_loop().run_in_executor(
            pool, functools.partial(get_non_transparent, url)
        ):
            await pixel_queue.put(pixel)


async def main():
    token = await get_token()

    async with aiohttp.ClientSession(headers=headers) as session:
        for x in range(0, 2):
            tasks.append(asyncio.create_task(parser(session)))

    tasks.append(asyncio.create_task(redis_feeder()))

    for x in range(0, 4):
        tasks.append(asyncio.create_task(graphql_parser(token)))

    await asyncio.gather(*tasks)


async def graphql_parser(token: str):
    transport = WebsocketsTransport(
        url="wss://gql-realtime-2.reddit.com/query",
        headers={
            "Authorization": f"Bearer {token}",
            "Sec-WebSocket-Protocol": "graphql-ws",
            "Origin": "https://hot-potato.reddit.com",
        },
    )

    # Using `async with` on the client will start a connection on the transport
    # and provide a `session` variable to execute queries on this connection
    async with Client(
        transport=transport,
        fetch_schema_from_transport=True,
    ) as session:
        print("socket connected")
        pixels_get = []

        while running or pixel_queue.qsize() > 0:
            while len(pixels_get) < 6:
                while pixel_queue.qsize() == 0:
                    await asyncio.sleep(0.25)

                try:
                    async with async_timeout.timeout(0.25):
                        payload = await pixel_queue.get()
                        pixels_get.append(payload)
                except asyncio.TimeoutError:
                    break

            if len(pixels_get) == 6:
                variables = {}
                pixels_index = {}

                for index, pixel in enumerate(pixels_get):
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

                result = await session.execute(
                    query_get_pixel_8x, variable_values=variables
                )

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
                        priority=10,
                    )
            else:
                # unhappy path: nopack of 8 pixels
                for payload in pixels_get:
                    x, y = payload
                    x = int(x)
                    y = int(y)

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

                    result = await session.execute(
                        query_get_pixel, variable_values=variables
                    )

                    pixel = result["act"]["data"][0]["data"]
                    update_pixel.apply_async(
                        kwargs=dict(
                            board_id=1,
                            x=x,
                            y=y,
                            pixel_data=pixel,
                        ),
                        priority=10,
                    )

            pixels_get.clear()


async def redis_feeder():
    async with ctx_aioredis() as redis:
        psub = redis.pubsub()

        async def reader(channel: aioredis.client.PubSub):
            while running:
                try:
                    async with async_timeout.timeout(1):
                        message = await channel.get_message(
                            ignore_subscribe_messages=True
                        )
                        if message is not None:
                            try:
                                payload = json.loads(message["data"])
                            except json.JSONDecodeError:
                                continue
                            await payload_queue.put(payload)
                        await asyncio.sleep(0.01)
                except asyncio.TimeoutError:
                    pass

        async with psub as p:
            await p.subscribe("socket:snakebin")
            await reader(p)

        # closing all open connections
        await psub.close()


if __name__ == "__main__":
    asyncio.run(main())
