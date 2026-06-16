from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.build_fit import evaluate_build_fit, import_build
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from build_fit_helpers import matching_account_gear, partial_account_gear, sample_build_import


def test_build_fit_score_uses_weighted_components() -> None:
    temp_dir = Path(".test_tmp") / f"build-score-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'builds.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            build = import_build(session, sample_build_import())

        full_fit = evaluate_build_fit(build, matching_account_gear())
        partial_fit = evaluate_build_fit(build, partial_account_gear())

        assert full_fit.score.score > partial_fit.score.score
        assert full_fit.score.playable_now is True
        assert partial_fit.score.gear_match < 1.0
    finally:
        close_database()
