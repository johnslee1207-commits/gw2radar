from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.report_engine import (
    ReportExportFormat,
    create_report_entitlement,
    ensure_default_report_products,
    generate_report_job,
    get_report_job,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph


def test_report_export_job_status_persists() -> None:
    temp_dir = Path(".test_tmp") / f"reports-job-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'reports.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "legendary_gap_report")
            job = generate_report_job(
                session,
                build_mock_graph(),
                user_id="local-user",
                product_id="legendary_gap_report",
                goal_id="gw2:goal:aurora",
                export_format=ReportExportFormat.HTML,
                output_root=temp_dir / "outputs",
            )
            loaded = get_report_job(session, job.job_id)

        assert loaded is not None
        assert loaded.job_id == job.job_id
        assert loaded.status == "succeeded"
        assert str(loaded.artifact_path).endswith(".html")
    finally:
        close_database()
