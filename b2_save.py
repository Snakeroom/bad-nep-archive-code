import asyncio
import functools
import json
import logging
from concurrent.futures import ThreadPoolExecutor

import aioredis
import async_timeout

from placedump.common import ctx_aioredis, get_b2_api
from placedump.tasks.pixels import download_url

logging.basicConfig(level=logging.INFO)
logging.getLogger("asyncio").setLevel(logging.DEBUG)

running = True

b2_api = get_b2_api()
b2_bucket = b2_api.get_bucket_by_name("erin-reddit-afd2022")

pool = ThreadPoolExecutor()


async def parse_message(payload):
    try:
        url = payload["payload"]["data"]["subscribe"]["data"]["name"]
    except KeyError:
        print(payload)
        return

    asyncio.get_event_loop().run_in_executor(
        pool, functools.partial(download_url.delay, url)
    )


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

                            try:
                                await parse_message(payload)
                            except Exception as e:
                                print(e)
                        await asyncio.sleep(0.01)
                except asyncio.TimeoutError:
                    pass

        async with psub as p:
            await p.subscribe("socket:snakebin")
            await reader(p)

        # closing all open connections
        await psub.close()


async def main():
    await redis_feeder()


if __name__ == "__main__":
    asyncio.run(main())
