import json

from placedump.common import ctx_redis
from placedump.tasks import app
from placedump.tasks.pixels import download_url


@app.task()
def parse_message(message: str):
    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        return

    # Get board ID from subscription number.
    board = min(
        int(payload.get("id", 2)) - 2,  # Default to root board if we have no ID.
        0,  # Default to first board if we something invalid.
    )

    # Attempt to handle based on message type.
    with ctx_redis() as redis:
        try:
            message_type = payload["payload"]["data"]["subscribe"]["data"]["__typename"]

            if message_type == "ConfigurationMessageData":
                highest_index = 0
                for canvas in payload["payload"]["data"]["subscribe"]["data"][
                    "canvasConfigurations"
                ]:
                    highest_index = max(canvas["index"], highest_index)
                redis.hset("place:meta", "index", highest_index)
        except KeyError:
            pass

    try:
        url = payload["payload"]["data"]["subscribe"]["data"]["name"]
    except KeyError:
        print(payload)
        return

    download_url.delay(board, url)
