from placedump.common import get_redis
from placedump.constants import socket_key

redis = get_redis()
last_id = "0"

while True:
    results = redis.xread({socket_key: last_id}, count=10000)
    if not results:
        break
    messages = results[0][1]
    for message_id, message in messages:
        last_id = message_id
        print(message["message"], end="")
