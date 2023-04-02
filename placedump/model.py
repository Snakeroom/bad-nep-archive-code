import os
from contextlib import contextmanager
from enum import Enum as PyEnum
from enum import unique
from typing import Generator

from cassandra.cluster import Cluster, Session
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
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.sql import func

db_url = os.environ.get("DB_URL", "sqlite:///test.db")
if "sqlite" in db_url:
    print("WARNING: Local SQLite DB in use, this may be unfavorable.")

# Cassandra
cass_cluster = Cluster(os.environ["CASSANDRA_HOSTS"].split(","))


@contextmanager
def ctx_cass() -> Generator[Session, None, None]:
    session = None

    try:
        session = cass_cluster.connect()
        yield session
    finally:
        if session:
            session.shutdown()


# SQL
engine = create_engine(db_url, future=True, pool_size=10, max_overflow=20)
sm = sessionmaker(engine)

async_engine = create_async_engine(
    db_url.replace("postgresql://", "postgresql+asyncpg://"),
    future=True,
)
async_sm = sessionmaker(async_engine, expire_on_commit=False, class_=AsyncSession)

Base = declarative_base()


class URL(Base):
    __tablename__ = "urls"

    def to_dict(self):
        return {"id": self.id, "url": self.url}

    id = Column(Integer, primary_key=True)

    url = Column(String, unique=True)
    fetched = Column(DateTime, server_default=func.now())
    size = Column(Integer)


class Pixel(Base):
    __tablename__ = "pixels"

    def to_dict(self):
        return {
            "canvas": self.board_id,
            "x": self.x,
            "y": self.y,
            "user": self.user,
            "modified": self.modified,
        }

    board_id = Column(Integer, primary_key=True)

    x = Column(Integer, nullable=False, primary_key=True)
    y = Column(Integer, nullable=False, primary_key=True)
    modified = Column(DateTime, nullable=False, primary_key=True)

    user = Column(String, nullable=False)
