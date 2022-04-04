import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from placedump.model import Pixel, async_sm
from pydantic import BaseModel
from sqlalchemy import func, select

app = FastAPI()


class PixelResult(BaseModel):
    canvas: int
    user: str
    x: int
    y: int
    modified: datetime.datetime


class CountableBase(BaseModel):
    count: int
    generated: datetime.datetime


class PixelList(CountableBase):
    history: List[PixelResult]


class PixelInfo(CountableBase):
    pass


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/info", response_model=PixelInfo)
async def info():
    async with async_sm() as db:
        count_query = select(func.count()).select_from(Pixel)
        pixel_count = await db.execute(count_query)
        pixel_count = pixel_count.scalar_one()

    return {"count": pixel_count, "generated": datetime.datetime.utcnow()}


@app.get("/pixel", response_model=PixelList)
async def get_pixel_history(
    x: Optional[int] = Query(None, ge=0),
    y: Optional[int] = Query(None, ge=0),
    canvas_id: Optional[int] = Query(None, ge=-1),
    author: Optional[str] = None,
    limit: Optional[int] = Query(100, ge=0),
    after: Optional[int] = None,
):
    """Get the history of pixels in a location or by author.

    This call accepts positions with X, Y coordinates, without a canvas.

    This call accepts positions with X, Y coordinates in specific canvases.

    This call accepts authors to pull pixels changed by that author.

    This call accepts no arguments to pull pixels for the entire dataset.
    """

    # GOOD ENOUGH HACK
    if canvas_id is None:
        canvas_id = 0

        if x and x > 999:
            canvas_id += 1
            x -= 999

        if y and y > 999:
            canvas_id += 2
            y -= 999

    async with async_sm() as db:
        # Create count query, no limits.
        count_query = select(func.count()).select_from(Pixel)

        # Query all with limit.
        filter_query = select(Pixel).order_by(Pixel.modified).limit(limit)

        if after is not None:
            timestamp = float(after) / 1000.0
            timestamp = datetime.datetime.fromtimestamp(timestamp)
            count_query = count_query.filter(Pixel.modified >= timestamp)
            filter_query = filter_query.filter(Pixel.modified >= timestamp)

        # Canvas
        if canvas_id is not None:
            count_query = count_query.filter(Pixel.board_id == canvas_id)
            filter_query = filter_query.filter(Pixel.board_id == canvas_id)

        # X filters
        if x is not None:
            count_query = count_query.filter(Pixel.x == x)
            filter_query = filter_query.filter(Pixel.x == x)

        # Y filters
        if y is not None:
            count_query = count_query.filter(Pixel.y == y)
            filter_query = filter_query.filter(Pixel.y == y)

        # Filter: Author
        if author is not None:
            count_query = count_query.filter(Pixel.user == author)
            filter_query = filter_query.filter(Pixel.user == author)

        # Execute queries.
        pixel_count = await db.execute(count_query)
        pixel_count = pixel_count.scalar_one()

        filtered_pixels = (await db.execute(filter_query)).scalars()
        pixels = [x.to_dict() for x in filtered_pixels]

    return {
        "count": pixel_count,
        "generated": datetime.datetime.utcnow(),
        "history": pixels,
    }
