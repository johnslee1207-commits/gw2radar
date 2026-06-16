from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.growth import CmsPageType, get_page
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_cms_content_includes_api_key_safety_page() -> None:
    temp_dir = Path(".test_tmp") / f"growth-cms-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'growth.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            page = get_page(session, "api-key-safety")

        assert page is not None
        assert page.page_type is CmsPageType.API_KEY_SAFETY
        assert "API keys are never returned" in page.body_markdown
    finally:
        close_database()
