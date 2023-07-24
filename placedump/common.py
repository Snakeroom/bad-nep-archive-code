import os
import re
import traceback
from contextlib import asynccontextmanager, contextmanager
from functools import lru_cache
from typing import AsyncGenerator, Generator, Optional

import aiohttp
import httpx
import redis
from b2sdk.v2 import B2Api, InMemoryAccountInfo
from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport
from gql.transport.websockets import WebsocketsTransport
from redis import asyncio as aioredis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost")
TOKEN_REGEX = re.compile(r'"accessToken":"([^"]+)"')
headers = {"User-Agent": "r/place archiver u/nepeat nepeat#0001"}


def get_redis(
    decode_responses: bool = True,
    db: int = 0,
) -> redis.Redis:
    return redis.from_url(
        REDIS_URL,
        decode_responses=decode_responses,
        db=db,
    )


def get_aioredis(decode_responses: bool = True):
    return aioredis.from_url(REDIS_URL, decode_responses=decode_responses)


@asynccontextmanager
async def ctx_aioredis(decode_responses=True) -> AsyncGenerator[aioredis.Redis, None]:
    try:
        redis = await get_aioredis(decode_responses)
        yield redis
    finally:
        await redis.close()


@contextmanager
def ctx_redis(decode_responses=True) -> Generator[redis.Redis, None, None]:
    try:
        redis = get_redis(decode_responses=decode_responses)
        yield redis
    finally:
        redis.close()


async def get_token() -> str:
    async with ctx_aioredis() as redis:
        token = await redis.get("reddit:token")
        if not token:
            async with aiohttp.ClientSession(headers=headers) as session:
                place_req = await session.get(
                    "https://www.reddit.com/r/place/?rdt=33146",
                )
                content = await place_req.text()
                matches = TOKEN_REGEX.search(content)
                if not matches:
                    print(token)
                    raise Exception("unable to get access token")
                token = matches.group(1)

                await redis.setex("reddit:token", 60, token)

    return token


def get_token_sync() -> str:
    with ctx_redis() as redis:
        token = redis.get("reddit:token")

        if not token:
            token_req = httpx.get("https://www.reddit.com/r/place/", headers=headers)
            content = token_req.text
            matches = TOKEN_REGEX.search(content)
            token = matches.group(1)
            redis.setex("reddit:token", 60, token)

    return token


def get_gql_client(token: Optional[str] = None) -> Client:
    if not token:
        token = get_token_sync()

    # Select your transport with a defined url endpoint
    transport = AIOHTTPTransport(
        url="https://gql-realtime-2.reddit.com/query",
        headers={
            "Authorization": f"Bearer {token}",
            "Origin": "https://hot-potato.reddit.com",
        },
    )

    # Create a GraphQL client using the defined transport
    return Client(transport=transport, fetch_schema_from_transport=False)


@asynccontextmanager
async def get_async_gql_client() -> Client:
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

    async with Client(
        transport=transport,
        fetch_schema_from_transport=True,
    ) as session:
        yield session


@lru_cache
def get_b2_api() -> B2Api:
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    application_key_id = os.environ["B2_KEY"]
    application_key = os.environ["B2_SECRET"]
    b2_api.authorize_account("production", application_key_id, application_key)

    return b2_api


def handle_exception(*args, **kwargs):
    traceback.print_exception(kwargs["exception"])
