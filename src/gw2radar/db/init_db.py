from sqlalchemy.engine import Engine

from gw2radar.db.models import Base
from gw2radar.db import session as db_session


def init_db(db_engine: Engine | None = None) -> None:
    Base.metadata.create_all(bind=db_engine or db_session.engine)
