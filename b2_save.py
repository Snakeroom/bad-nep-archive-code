import asyncio
import functools
import json
import logging
from concurrent.futures import ThreadPoolExecutor

import aiohttp
import aioredis
import async_timeout
import requests

from placedump.common import ctx_aioredis, get_b2_api, headers

logging.basicConfig(level=logging.INFO)
logging.getLogger("asyncio").setLevel(logging.DEBUG)

running = True
tasks = []
payload_queue = asyncio.Queue()

b2_api = get_b2_api()
b2_bucket = b2_api.get_bucket_by_name("erin-reddit-afd2022")

pool = ThreadPoolExecutor(max_workers=8)


def upload_file(filename, content):
    b2_bucket.upload_bytes(content, filename)


def fetch_file(url: str):
    filename = url.replace("https://", "")

    request = requests.get(url, headers=headers)
    print(filename, payload_queue.qsize())
    upload_file(filename, request.content)


async def parse_message(session: aiohttp.ClientSession, payload):
    try:
        url = payload["payload"]["data"]["subscribe"]["data"]["name"]
    except KeyError:
        print(payload)
        return

    asyncio.get_event_loop().run_in_executor(pool, functools.partial(fetch_file, url))


async def url_fetcher(session: aiohttp.ClientSession):
    while running or payload_queue.qsize() > 0:
        while payload_queue.qsize() == 0:
            await asyncio.sleep(0.25)
        payload = await payload_queue.get()
        await parse_message(session, payload)
        payload_queue.task_done()


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


async def main():
    global running

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            for _ in range(0, 8):
                tasks.append(asyncio.create_task(url_fetcher(session)))

        await redis_feeder()
    except KeyboardInterrupt:
        running = False
        for task in tasks:
            await task


if __name__ == "__main__":
    asyncio.run(main())
