import asyncio
import json
import random

import backoff
from gql import Client
from gql.transport.websockets import WebsocketsTransport

from placedump.common import ctx_aioredis, ctx_redis, get_token, headers
from placedump.constants import query_get_pixel_8x
from placedump.tasks.pixels import update_pixel

running = True
tasks = []


async def main():
    for x in range(0, 4):
        tasks.append(asyncio.create_task(graphql_parser()))

    await asyncio.gather(*tasks)


@backoff.on_exception(backoff.constant, Exception, interval=1, max_time=300)
async def graphql_parser():
    token = await get_token()

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
    async with ctx_aioredis() as redis:
        async with Client(
            transport=transport,
            fetch_schema_from_transport=True,
        ) as session:
            print("socket connected")
            pixels_get = []

            highest_board = await redis.hget("place:meta", "index")
            highest_board = max(int(highest_board), 0)

            while running:
                for pair in await redis.spop("queue:pixels", 8):
                    pair = json.loads(pair)
                    pixels_get.append((pair["x"], pair["y"], pair["board"]))

                # sleep if we have no pixels
                if len(pixels_get) == 0:
                    await asyncio.sleep(0.1)
                    continue

                # pad pixels if less than payload size
                while len(pixels_get) < 8:
                    pixels_get.append(
                        (
                            random.randint(0, 999),
                            random.randint(0, 999),
                            random.randint(0, highest_board + 1),
                        )
                    )

                variables = {}
                pixels_index = {}

                for index, pixel in enumerate(pixels_get):
                    x, y, board = pixel

                    variables["input" + str(index + 1)] = {
                        "actionName": "r/replace:get_tile_history",
                        "PixelMessageData": {
                            "canvasIndex": board,
                            "colorIndex": 0,
                            "coordinate": {"x": x, "y": y},
                        },
                    }
                    pixels_index["input" + str(index + 1)] = (x, y, board)

                result = await session.execute(
                    query_get_pixel_8x, variable_values=variables
                )

                for input_name, gql_res in result.items():
                    x, y, board = pixels_index[input_name]
                    pixel = gql_res["data"][0]["data"]

                    update_pixel.apply_async(
                        kwargs=dict(
                            board_id=board,
                            x=x,
                            y=y,
                            pixel_data=pixel,
                        ),
                        priority=5,
                    )
                print("batch completed, remaining: ", await redis.scard("queue:pixels"))
                pixels_get.clear()


if __name__ == "__main__":
    asyncio.run(main())
