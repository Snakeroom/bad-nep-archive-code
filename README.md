# placedump

Toolset to make a best effort attempt to grab all r/place (2022) WebSocket messages, pixels, and canvases.

## Layout

Documenting layout which powered archival and parsing for the last 1.5 days of r/place.

### `dump.py`
* Connects to Reddit's live servers and subscribes to all r/place canvas changes and config changes
* Saves all messages to a Redis stream for later parsing
* Pushes all messagesto a Redit PubSub channel

### `pixel_watcher.py`
* Connects to Reddit's live servers to query pixel statuses in bulk to save on HTTP requests and data.
* Fetches pixels in bulk from a Redis set `queue:pixels`
* Spawns Celery task `pixels.update_pixel` for every pixel result from Reddit

### Celery
* Main job queue for message processing
* Redis used for job result storage and queuing

### Celery: Tasks
* `parse.parse_message` 
    - Parse GraphQL responses from the live WS
    - Canvas responses updated the current canvas ID
    - All pixel updates spawns a `pixels.download_url` task
* `pixels.download_url`
    - Downloads URL passed into function
    - Uploads URL and result straight into Backblaze B2
    - Spawns `pixels.get_non_transparent` task
    - Adds URL into database
* `pixels.update_pixel`
    - Postgres upsert insert for the Pixel table
    - Very inefficient but it did the job!
    - 192 processes were needed to handle the workload for this task
    - Certainly could have been improved with batching
* `pixels.get_pixel`
    - Gets a single pixel from Reddit and calls `pixels.update_pixel`
    - Very inefficient
    - Guaranteed rate limit!
* `pixels.get_non_transparent`
    - Thanks Stack Overflow. https://stackoverflow.com/questions/60051941/find-the-coordinates-in-an-image-where-a-specified-colour-is-detected
    - Parses a PNG passed as bytes over Celery and adds all pixels to Redis set `queue:pixels`
    - Returns all pixels as a list.

## dev runbook
```
# forever loop alias
run_forever() { while :; do "$@"; sleep 1; done }

# deploy dump stack
export DOCKER_HOST=unix:///tmp/docker.sock
docker stack deploy -c docker-compose.yml --with-registry-auth placedump
```