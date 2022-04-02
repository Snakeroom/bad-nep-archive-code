import asyncio
import functools
import json
import logging
import random
import re
from concurrent.futures import ThreadPoolExecutor

import aiohttp
import aioredis

from placedump.common import ctx_aioredis, get_token, headers
from placedump.tasks.parse import parse_message

logging.basicConfig(level=logging.INFO)

tasks = []

pool = ThreadPoolExecutor(max_workers=8)

PAYLOAD_CONFIG = """
  subscription configuration($input: SubscribeInput!) {
    subscribe(input: $input) {
      id
      ... on BasicMessage {
        data {
          __typename
          ... on ConfigurationMessageData {
            colorPalette {
              colors {
                hex
                index
              }
            }
            canvasConfigurations {
              index
              dx
              dy
            }
            canvasWidth
            canvasHeight
          }
        }
      }
    }
  }
"""

PAYLOAD_REPLACE = """
  subscription replace($input: SubscribeInput!) {
    subscribe(input: $input) {
      id
      ... on BasicMessage {
        data {
          __typename
          ... on FullFrameMessageData {
            __typename
            name
            timestamp
          }
          ... on DiffFrameMessageData {
            __typename
            name
            currentTimestamp
            previousTimestamp
          }
        }
      }
    }
  }
"""


async def push_to_key(redis: aioredis.Redis, key: str, payload: dict):
    await redis.xadd(key, payload, maxlen=2000000)

    message = payload["message"]
    if isinstance(message, bytes):
        message = message.decode("utf8")

    await redis.publish(key, message)
    parse_message.delay(message)


async def connect_socket(session: aiohttp.ClientSession, url: str):
    token = await get_token()
    print(token)

    async with session.ws_connect(
        url,
        headers={
            "Sec-WebSocket-Protocol": "graphql-ws",
            "Origin": "https://hot-potato.reddit.com",
        },
    ) as ws:
        await ws.send_str(
            json.dumps(
                {
                    "type": "connection_init",
                    "payload": {"Authorization": f"Bearer {token}"},
                }
            )
        )

        await ws.send_json(
            {
                "id": "1",
                "payload": {
                    "extensions": {},
                    "operationName": "configuration",
                    "query": PAYLOAD_CONFIG,
                    "variables": {
                        "input": {
                            "channel": {
                                "category": "CONFIG",
                                "teamOwner": "AFD2022",
                            }
                        }
                    },
                },
                "type": "start",
            }
        )

        await ws.send_json(
            {
                "id": "2",
                "payload": {
                    "extensions": {},
                    "operationName": "replace",
                    "query": PAYLOAD_REPLACE,
                    "variables": {
                        "input": {
                            "channel": {
                                "category": "CANVAS",
                                "tag": "0",
                                "teamOwner": "AFD2022",
                            }
                        }
                    },
                },
                "type": "start",
            }
        )

        socket_key = "socket:snakebin"
        async with ctx_aioredis(decode_responses=False) as redis:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await push_to_key(
                        redis,
                        socket_key,
                        {
                            "message": msg.data.encode("utf8"),
                            "type": "text",
                        },
                    )
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    await push_to_key(
                        redis,
                        socket_key,
                        {
                            "message": msg.data,
                            "type": "binary",
                        },
                    )
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break


async def main():
    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            try:
                await connect_socket(session, "wss://gql-realtime-2.reddit.com/query")
                print("Socket disconnected!")
            except aiohttp.client_exceptions.WSServerHandshakeError as e:
                print(e.request_info)
                print("Handshake error!", e)

            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
