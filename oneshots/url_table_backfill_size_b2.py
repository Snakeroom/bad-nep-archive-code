import datetime
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import List

import ujson as json
from placedump.common import get_b2_api, get_redis
from placedump.constants import socket_key
from placedump.model import URL, Pixel, sm
from placedump.tasks.pixels import download_url
from sqlalchemy import func, select

db = sm()
b2 = get_b2_api()
bucket = b2.get_bucket_by_name("erin-reddit-afd2022")

update_batch = []
url_map = {}
i = 0


def commit_batch(sql, batch: List[str]):
    sql.bulk_update_mappings(
        URL,
        batch,
    )
    db_insert.commit()
    print("commited", i)
    batch.clear()


for url_item in db.execute(select(URL)).scalars():
    url_map[url_item.url] = url_item.id

print("loaded", len(url_map))

with sm() as db_insert:
    for file_version, folder_name in bucket.ls(
        folder_to_list="hot-potato.reddit.com/media/canvas-images", latest_only=True
    ):
        fixed_url = "https://" + file_version.file_name

        if file_version.size and fixed_url in url_map:
            update_batch.append(
                {
                    "id": url_map[fixed_url],
                    "size": file_version.size,
                }
            )
            i += 1

        if len(update_batch) > 1024:
            commit_batch(db_insert, update_batch)

    commit_batch(db_insert, update_batch)
    i += 1
