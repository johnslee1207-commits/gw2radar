from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.build_fit import build_transition_plan, import_build, match_account_gear
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from build_fit_helpers import partial_account_gear, sample_build_import


def test_gear_transition_cost_sums_missing_requirements() -> None:
    temp_dir = Path(".test_tmp") / f"build-transition-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'builds.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            build = import_build(session, sample_build_import())

        matches = match_account_gear(build, partial_account_gear())
        plan = build_transition_plan(build, matches)

        assert plan.estimated_cost_gold == 30
        assert len(plan.missing_requirements) == 2
        assert all("Manually review" in step for step in plan.manual_steps)
    finally:
        close_database()
