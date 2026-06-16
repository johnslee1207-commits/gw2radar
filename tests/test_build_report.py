from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.build_fit import evaluate_build_fit, import_build, render_build_fit_report
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from build_fit_helpers import partial_account_gear, sample_build_import


def test_build_report_contains_required_sections_and_boundaries() -> None:
    temp_dir = Path(".test_tmp") / f"build-report-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'builds.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            build = import_build(session, sample_build_import())

        report = render_build_fit_report(evaluate_build_fit(build, partial_account_gear()))

        assert "Build Fit Report" in report
        assert "Fit Score" in report
        assert "Gear Reuse" in report
        assert "Transition Plan" in report
        assert "Budget Alternative" in report
        assert "No gameplay automation or automatic gear changes" in report
    finally:
        close_database()
