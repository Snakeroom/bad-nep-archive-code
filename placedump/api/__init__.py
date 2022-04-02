import datetime
from typing import List

from fastapi import FastAPI
from placedump.model import Pixel, async_sm
from pydantic import BaseModel
from sqlalchemy import func, select

app = FastAPI()


class PixelResult(BaseModel):
    canvas: int
    x: int
    y: int
    modified: datetime.datetime


class CountableBase(BaseModel):
    count: int
    generated: datetime.datetime


class PixelList(CountableBase):
    pixels: List[PixelResult]


class PixelInfo(CountableBase):
    pass


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/pixels", response_model=PixelInfo)
async def pixels():
    async with async_sm() as db:
        count_query = select(func.count()).select_from(Pixel)
        pixel_count = await db.execute(count_query)
        pixel_count = pixel_count.scalar_one()

    return {"count": pixel_count, "generated": datetime.datetime.utcnow()}


@app.get("/pixels/author/<author: str>", response_model=PixelList)
async def get_pixel_history_by_author(author: str):
    async with async_sm() as db:
        # Count all.
        count_query = (
            select(func.count())
            .select_from(Pixel)
            .filter(func.lower(Pixel.user) == author.lower())
        )

        pixel_count = await db.execute(count_query)
        pixel_count = pixel_count.scalar_one()

        # Query all.
        filter_query = select(Pixel).filter(func.lower(Pixel.user) == author.lower())
        filtered_pixels = (await db.execute(filter_query)).scalars()

        pixels = [x.to_dict() for x in filtered_pixels]

    return {
        "count": pixel_count,
        "generated": datetime.datetime.utcnow(),
        "pixels": pixels,
    }


@app.get("/pixels/canvas/<canvas: int>/<x: int>/<y: int>")
async def get_pixel_history_by_cords(canvas: int, x: int, y: int):
    """Get the history of a specific pixel.
    Using a value of -1 for canvas will get it for all canvases."""
    async with async_sm() as db:
        count_query = (
            select(func.count())
            .select_from(Pixel)
            .filter(Pixel.x == x)
            .filter(Pixel.y == y)
        )

        if canvas != -1:
            count_query = count_query.filter(Pixel.board_id == canvas)

        pixel_count = await db.execute(count_query)
        pixel_count = pixel_count.scalar_one()

        # Query all.
        filter_query = select(Pixel).filter(Pixel.x == x).filter(Pixel.y == y)

        if canvas != -1:
            filter_query = filter_query.filter(Pixel.board_id == canvas)
        filtered_pixels = (await db.execute(filter_query)).scalars()

        pixels = [x.to_dict() for x in filtered_pixels]

    return {
        "count": pixel_count,
        "generated": datetime.datetime.utcnow(),
        "pixels": pixels,
    }
