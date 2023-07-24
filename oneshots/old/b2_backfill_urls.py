import asyncio
import functools
import json
import logging
from concurrent.futures import ThreadPoolExecutor

import requests
from placedump.common import ctx_aioredis, get_b2_api, headers

logging.basicConfig(level=logging.INFO)
logging.getLogger("asyncio").setLevel(logging.DEBUG)

running = True

b2_api = get_b2_api

b2_bucket = b2_api.get_bucket_by_name("erin-reddit-afd2022")

pool = ThreadPoolExecutor(max_workers=4)


def upload_file(filename, content):
    b2_bucket.upload_bytes(content, filename)


def fetch_file(url: str):
    filename = url.replace("https://", "")

    request = requests.get(url, headers=headers)
    request.raise_for_status()

    print(filename, request.status_code, request.headers["Content-Type"])
    upload_file(filename, request.content)


urls = []

with open("urls", "r") as f:
    for line in f.readlines():
        line = line.strip()
        urls.append(line)

pool.map(fetch_file, urls)
