from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.growth import list_pages
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_landing_pages_seed_core_commercial_pages() -> None:
    temp_dir = Path(".test_tmp") / f"growth-pages-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'growth.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            pages = list_pages(session)

        slugs = {page.slug for page in pages}
        assert {"home", "legendary-planner", "build-fit", "market-radar", "pricing"} <= slugs
        assert all(page.seo.title for page in pages)
    finally:
        close_database()
