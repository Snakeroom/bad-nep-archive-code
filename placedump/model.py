import os
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func

db_url = os.environ.get("DB_URL", "sqlite:///test.db")
if "sqlite" in db_url:
    print("WARNING: Local SQLite DB in use, this may be unfavorable.")

engine = create_engine(db_url, future=True)
sm = sessionmaker(engine)

Base = declarative_base()


class Board(Base):
    __tablename__ = "boards"

    def to_dict(self):
        return {"id": self.id}

    board_id = Column(Integer, primary_key=True)


class Pixel(Base):
    __tablename__ = "pixels"

    def to_dict(self):
        return {
            "board": self.board_id,
            "x": self.x,
            "y": self.y,
            "user": self.user,
            "modified": self.modified,
        }

    board_id = Column(Integer)

    x = Column(Integer, nullable=False)
    y = Column(Integer, nullable=False)

    user = Column(String, nullable=False)
    modified = Column(DateTime, nullable=False)


Index("pixel_unique_mod", Pixel.x, Pixel.y, Pixel.modified, primary_key=True)
