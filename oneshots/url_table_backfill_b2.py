import datetime
import sys
from concurrent.futures import ThreadPoolExecutor

import ujson as json
from placedump.common import get_b2_api, get_redis
from placedump.constants import socket_key
from placedump.model import URL, Pixel, sm
from placedump.tasks.pixels import download_url
from sqlalchemy import func, select

db = sm()
b2 = get_b2_api()
sql_url = set()
bucket = b2.get_bucket_by_name("erin-reddit-afd2022")

for url in db.execute(select(URL)).scalars():
    sql_url.add(url.url)

print(len(sql_url), "in database")

urls_to_insert = []

with sm() as db_insert:
    for file_version, folder_name in bucket.ls(
        folder_to_list="hot-potato.reddit.com/media/canvas-images", latest_only=True
    ):
        fixed_url = "https://" + file_version.file_name
        if fixed_url in sql_url:
            continue

        timestamp = float(file_version.upload_timestamp) / 1000.0
        timestamp = datetime.datetime.fromtimestamp(timestamp)

        urls_to_insert.append(
            {
                "url": fixed_url,
                "fetched": timestamp,
            }
        )

        if len(urls_to_insert) > 1024:
            db_insert.bulk_insert_mappings(
                URL,
                urls_to_insert,
            )
            db_insert.commit()
            print("Added 1024 URLs.")
            urls_to_insert.clear()

    db_insert.bulk_insert_mappings(
        URL,
        urls_to_insert,
    )
    db_insert.commit()
    print(f"Added {len(urls_to_insert)} URLs.")
