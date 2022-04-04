import ujson
from placedump.common import get_redis

redis = get_redis()

for x in range(0, 1000):
    for y in range(0, 1000):
        redis.sadd(
            "queue:pixels",
            ujson.dumps(
                {
                    "x": str(x),
                    "y": str(y),
                    "board": "0",
                }
            ),
        )
