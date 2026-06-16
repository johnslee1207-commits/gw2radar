from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.build_fit import evaluate_build_fit, import_build
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from build_fit_helpers import partial_account_gear, sample_build_import


def test_build_fit_never_claims_automatic_gear_changes() -> None:
    temp_dir = Path(".test_tmp") / f"build-no-auto-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'builds.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            build = import_build(session, sample_build_import())

        result = evaluate_build_fit(build, partial_account_gear())
        text = " ".join(result.transition_plan.manual_steps).lower()

        assert "manual" in text
        assert "automatic" not in text
        assert result.transition_plan.recommendation_boundary == "informational_manual_actions_only"
    finally:
        close_database()
