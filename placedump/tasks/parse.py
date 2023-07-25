import json

from placedump.common import ctx_redis
from placedump.tasks import app
from placedump.tasks.pixels import download_url


@app.task(
    autoretry_for=(Exception,),
    retry_backoff=2,
)
def parse_message(message: str, canvas_id: int = None):
    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        return

    # Get canvas ID from subscription number.
    if not canvas_id:
        canvas_id = min(
            int(payload.get("id", 2)) - 2,  # Default to root board if we have no ID.
            0,  # Default to first board if we something invalid.
        )

    # Attempt to handle based on message type.
    with ctx_redis() as redis:
        try:
            message_type = payload["subscribe"]["data"]["__typename"]

            if message_type == "ConfigurationMessageData":
                highest_index = 0
                for canvas in payload["subscribe"]["data"]["canvasConfigurations"]:
                    highest_index = max(canvas["index"], highest_index)
                redis.hset("place:meta", "index", highest_index)
        except KeyError:
            pass

    try:
        url = payload["subscribe"]["data"]["name"]
    except KeyError:
        try:
            url = payload["payload"]["data"]["subscribe"]["data"]["name"]
        except KeyError:
            print(payload)
            return

    download_url.delay(canvas_id, url)
