from pathlib import Path
from uuid import uuid4

import pytest

from gw2radar.commercial.growth import list_pages, validate_required_trust_pages
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.models import CmsPageModel
from gw2radar.db.session import close_database, configure_database


def test_privacy_and_trust_pages_are_required() -> None:
    temp_dir = Path(".test_tmp") / f"growth-privacy-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'growth.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            pages = list_pages(session)
            slugs = {page.slug for page in pages}
            assert {"privacy", "terms", "api-key-safety"} <= slugs
            session.query(CmsPageModel).filter(CmsPageModel.slug == "privacy").delete()
            session.commit()
            with pytest.raises(ValueError):
                validate_required_trust_pages(session)
    finally:
        close_database()
