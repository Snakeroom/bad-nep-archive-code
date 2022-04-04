import sys
from concurrent.futures import ThreadPoolExecutor

import ujson as json
from placedump.common import get_redis
from placedump.constants import socket_key
from placedump.model import URL, sm
from placedump.tasks.pixels import download_url
from sqlalchemy import func, select

db = sm()
redis = get_redis()
sql_url = set()
to_backfill = set()
last_id = "0"
pool = ThreadPoolExecutor(max_workers=8)

for url in db.execute(select(URL)).scalars():
    sql_url.add(url.url)

print(len(sql_url), "in database")

while True:
    results = redis.xread({socket_key: last_id}, count=10000)
    if not results:
        break
    messages = results[0][1]
    for message_id, message in messages:
        last_id = message_id
        decoded = json.loads(message["message"])

        # get canvas id

        # get url
        try:
            if decoded["type"] in ["ka", "connection_ack"]:
                continue

            if (
                decoded["payload"]["data"]["subscribe"]["data"]["__typename"]
                == "ConfigurationMessageData"
            ):
                continue
        except KeyError:
            continue

        try:
            url = decoded["subscribe"]["data"]["name"]
            canvas_id = decoded.get("canvas_id", int(decoded.get("id", 2)) - 2)
        except KeyError:
            try:
                url = decoded["payload"]["data"]["subscribe"]["data"]["name"]
                canvas_id = int(decoded.get("id", 2)) - 2
            except KeyError:
                continue

        if url not in sql_url:
            to_backfill.add((canvas_id, url))

print(len(to_backfill), "to backfill")


for item in to_backfill:
    download_url.apply_async(
        args=(item[0], item[1]),
        priority=10,
    )
    sys.stdout.write(".")
    sys.stdout.flush()
