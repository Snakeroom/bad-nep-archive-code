from placedump.common import get_redis, get_token, get_token_sync


async def test_token_get():
    redis = get_redis()

    token_1 = await get_token()
    token_2 = await get_token()

    assert token_1 == token_2
    assert redis.ttl("reddit:token") > 0
    redis.delete("reddit:token")


def test_token_sync_get_cached():
    redis = get_redis()

    token_1 = get_token_sync()
    token_2 = get_token_sync()

    assert token_1 == token_2
    assert redis.ttl("reddit:token") > 0
    redis.delete("reddit:token")
