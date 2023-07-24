import glob
import os.path
from concurrent.futures import ProcessPoolExecutor

from placedump.tasks.pixels import update_pixel

pool = ProcessPoolExecutor(max_workers=16)


def process_file(file):
    filename = os.path.split(file)[-1]
    x, y = filename.split("_")
    x = int(x)
    y = int(y)

    with open(file, "r") as f:
        for line in f.readlines():
            username, timestamp = line.strip().split(",")
            meta = {
                "userInfo": {
                    "username": username,
                },
                "lastModifiedTimestamp": timestamp,
            }

            print(x, y, meta)
            update_pixel.apply_async(
                args=(
                    1,
                    x,
                    y,
                    meta,
                )
            )


pool.map(process_file, glob.glob("pixels/*"))
