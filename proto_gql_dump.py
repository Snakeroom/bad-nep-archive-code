import asyncio
import json
import logging

import aioredis
import backoff
from gql import Client, gql
from gql.transport.websockets import WebsocketsTransport
from httpx import head

from placedump.common import ctx_aioredis, get_token
from placedump.constants import config_gql, socket_key, sub_gql
from placedump.tasks.parse import parse_message

log = logging.getLogger(__name__)
tasks = []


async def get_meta() -> dict:
    async with ctx_aioredis() as redis:
        result = await redis.hgetall("place:meta")
        return result or {}


async def push_to_key(redis: aioredis.Redis, key: str, payload: dict, canvas_id: int):
    await redis.xadd(key, payload, maxlen=2000000)

    message = payload["message"]
    await redis.publish(key, message)
    parse_message.delay(message, canvas_id)


async def main():
    meta = await get_meta()
    highest_board = int(meta.get("index", "0"))
    log.info(meta)

    tasks.append(asyncio.create_task(graphql_parser("config")))

    for x in range(0, highest_board + 1):
        tasks.append(asyncio.create_task(graphql_parser(x)))

    await asyncio.gather(*tasks)


@backoff.on_exception(backoff.constant, Exception, interval=1, max_time=300)
async def graphql_parser(canvas_id):
    token = await get_token()

    transport = WebsocketsTransport(
        url="wss://gql-realtime-2.reddit.com/query",
        headers={
            "Authorization": f"Bearer {token}",
            "Sec-WebSocket-Protocol": "graphql-ws",
            "Origin": "https://hot-potato.reddit.com",
            "User-Agent": "r/place archiver u/nepeat nepeat#0001",
        },
        ping_interval=2.0,
    )

    # pick the corrent gql schema and pick variables for canvas / config grabs.
    if canvas_id == "config":
        schema = config_gql
        variables = {
            "input": {
                "channel": {
                    "category": "CONFIG",
                    "teamOwner": "AFD2022",
                }
            }
        }
    else:
        schema = sub_gql
        variables = {
            "input": {
                "channel": {
                    "category": "CANVAS",
                    "teamOwner": "AFD2022",
                    "tag": str(canvas_id),
                }
            }
        }

    # Using `async with` on the client will start a connection on the transport
    # and provide a `session` variable to execute queries on this connection
    log.info("socket connecting for canvas %s", canvas_id)

    async with ctx_aioredis() as redis:
        async with Client(
            transport=transport,
            fetch_schema_from_transport=True,
        ) as session:
            log.info("socket connected for canvas %s", canvas_id)
            async for result in session.subscribe(schema, variable_values=variables):
                # append canvas id to messages
                result["canvas_id"] = canvas_id

                await push_to_key(
                    redis,
                    socket_key,
                    {
                        "message": json.dumps(result),
                        "type": "text",
                    },
                    canvas_id=canvas_id,
                )


if __name__ == "__main__":
    asyncio.run(main())
