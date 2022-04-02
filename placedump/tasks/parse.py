import json

from placedump.tasks import app
from placedump.tasks.pixels import download_url


@app.task()
def parse_message(message: str):
    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        return

    try:
        url = payload["payload"]["data"]["subscribe"]["data"]["name"]
    except KeyError:
        print(payload)
        return

    download_url.delay(url)
