import asyncio
import functools
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import backoff
from gql import gql
from gql.dsl import DSLQuery, DSLSchema, dsl_gql

from placedump.common import ctx_aioredis, get_async_gql_client, handle_backoff, headers
from placedump.tasks.pixels import update_pixel

log = logging.getLogger("info")
pool = ThreadPoolExecutor(max_workers=8)
running = True
tasks = []


async def main():
    for x in range(0, 4):
        tasks.append(asyncio.create_task(graphql_parser()))

    await asyncio.gather(*tasks)


@lru_cache
def generate_history_mutation(count: int):
    input_header = ""
    inputs = ""

    for input_index in range(0, count):
        index_str = str(input_index + 1)

        input_header += f"$input{index_str}: ActInput!, "
        inputs += """
    input%s: act(input: $input%s) {
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
    }""" % (
            index_str,
            index_str,
        )

    input_header = input_header.rstrip(", ")

    return gql(
        """mutation pixelHistory({input_header}) {{
        {inputs}
  }}""".format(
            input_header=input_header,
            inputs=inputs,
        )
    )


async def bulk_update(pixels: dict, gql_results: dict):
    updates = []

    for input_name, gql_res in gql_results.items():
        pixel_info = pixels[input_name]
        pixel_data = gql_res["data"][0]["data"]

        updates.append(
            asyncio.get_event_loop().run_in_executor(
                pool,
                functools.partial(
                    update_pixel.apply_async,
                    kwargs=dict(
                        board_id=pixel_info["board"],
                        x=pixel_info["x"],
                        y=pixel_info["y"],
                        pixel_data=pixel_data,
                    ),
                    priority=5,
                ),
            )
        )

    await asyncio.gather(*updates)


@backoff.on_exception(backoff.fibo, Exception, max_time=30, on_backoff=handle_backoff)
async def graphql_parser():
    # Using `async with` on the client will start a connection on the transport
    # and provide a `session` variable to execute queries on this connection
    async with ctx_aioredis() as redis:
        async with get_async_gql_client() as session:
            log.info("socket connected")
            pixels_index = {}

            highest_board = await redis.hget("place:meta", "index") or 0
            highest_board = max(int(highest_board), 0)

            while running:
                variables = {}

                pairs_raw = await redis.spop("queue:pixels", 24)
                for index, pixel in enumerate(pairs_raw):
                    pixels_index["input" + str(index + 1)] = json.loads(pixel)

                # sleep if we have no pixels
                if len(pixels_index) == 0:
                    await asyncio.sleep(0.1)
                    continue

                for key, pixel in pixels_index.items():
                    variables[key] = {
                        "actionName": "r/replace:get_tile_history",
                        "PixelMessageData": {
                            "canvasIndex": pixel["board"],
                            "colorIndex": 0,
                            "coordinate": {"x": pixel["x"], "y": pixel["y"]},
                        },
                    }

                gql_query = generate_history_mutation(len(pixels_index))

                result = await session.execute(
                    gql_query,
                    variable_values=variables,
                )

                await bulk_update(pixels_index, result)
                log.info(
                    "batch completed, batch: %s remaining: %s",
                    len(pixels_index),
                    await redis.scard("queue:pixels"),
                )

                pixels_index.clear()


if __name__ == "__main__":
    asyncio.run(main())
