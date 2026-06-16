from sqlalchemy.engine import Engine

from gw2radar.db.models import Base
from gw2radar.db.session import engine


def init_db(db_engine: Engine | None = None) -> None:
    Base.metadata.create_all(bind=db_engine or engine)
