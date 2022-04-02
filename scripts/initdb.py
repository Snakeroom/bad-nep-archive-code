import os

from alembic import command
from alembic.config import Config
from placedump.model import Base, engine


def init_db():
    engine.echo = True
    Base.metadata.create_all(engine)
    alembic_cfg = Config(
        os.path.dirname(os.path.realpath(__file__)) + "/../alembic.ini"
    )
    command.stamp(alembic_cfg, "head")


if __name__ == "__main__":
    init_db()
