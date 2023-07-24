import asyncio
import json
import logging

import backoff
from redis import asyncio as aioredis

from placedump.common import (
    ctx_aioredis,
    get_async_gql_client,
    get_token,
    handle_exception,
)
from placedump.constants import config_gql, socket_key, sub_gql
from placedump.tasks.parse import parse_message

log = logging.getLogger(__name__)
tasks = []
parsers = {}


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
    tasks.append(asyncio.create_task(graphql_parser("config")))
    tasks.append(asyncio.create_task(parser_launcher()))

    await asyncio.gather(*tasks)


async def parser_launcher():
    while True:
        meta = await get_meta()
        highest_board = int(meta.get("index", "0"))

        if len(parsers) < highest_board + 1:
            log.info("meta canvas count update, new meta is")
            log.info(meta)

            for x in range(0, highest_board + 1):
                if x not in parsers:
                    task = asyncio.create_task(graphql_parser(x))
                    parsers[x] = task
                    tasks.append(task)

        await asyncio.sleep(1)


@backoff.on_exception(backoff.fibo, Exception, max_time=30, on_backoff=handle_exception)
async def graphql_parser(canvas_id):
    # pick the corrent gql schema and pick variables for canvas / config grabs.
    if canvas_id == "config":
        schema = config_gql
        variables = {
            "input": {
                "channel": {
                    "category": "CONFIG",
                    "teamOwner": "GARLICBREAD",
                }
            }
        }
    else:
        schema = sub_gql
        variables = {
            "input": {
                "channel": {
                    "category": "CANVAS",
                    "teamOwner": "GARLICBREAD",
                    "tag": str(canvas_id),
                }
            }
        }

    # Using `async with` on the client will start a connection on the transport
    # and provide a `session` variable to execute queries on this connection
    log.info("socket connecting for canvas %s", canvas_id)

    async with ctx_aioredis() as redis:
        async with get_async_gql_client() as session:
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
