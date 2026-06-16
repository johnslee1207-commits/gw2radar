from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.build_fit import import_build, match_account_gear
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from build_fit_helpers import matching_account_gear, sample_build_import


def test_account_gear_matcher_reuses_matching_slots() -> None:
    temp_dir = Path(".test_tmp") / f"build-match-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'builds.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            build = import_build(session, sample_build_import())

        matches = match_account_gear(build, matching_account_gear())

        assert all(match.matched for match in matches)
        assert all(match.reusable_item_name for match in matches)
    finally:
        close_database()
