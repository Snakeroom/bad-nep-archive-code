import os
import re
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncGenerator

import aiohttp
import aioredis
import redis
from b2sdk.v2 import B2Api, InMemoryAccountInfo
from gql import Client
from gql.transport.aiohttp import AIOHTTPTransport

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost")
TOKEN_REGEX = re.compile(r'"accessToken":"([^"]+)"')
headers = {"User-Agent": "r/place archiver u/nepeat nepeat#0001"}


def get_redis(
    decode_responses: bool = True,
    db: int = 0,
) -> redis.Redis():
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


async def get_token() -> str:
    async with aiohttp.ClientSession(headers=headers) as session:
        place_req = await session.get("https://www.reddit.com/r/place/")
        content = await place_req.text()
    matches = TOKEN_REGEX.search(content)

    return matches.group(1)


def get_nb_client() -> Client:
    # Select your transport with a defined url endpoint
    transport = AIOHTTPTransport(
        url="https://gql-realtime-2.reddit.com/query",
    )

    # Create a GraphQL client using the defined transport
    return Client(transport=transport, fetch_schema_from_transport=True)


@lru_cache
def get_b2_api() -> B2Api:
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    application_key_id = os.environ["B2_KEY"]
    application_key = os.environ["B2_SECRET"]
    b2_api.authorize_account("production", application_key_id, application_key)

    return b2_api
