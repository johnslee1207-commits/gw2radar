from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.report_engine import (
    ReportExportFormat,
    create_report_entitlement,
    ensure_default_report_products,
    generate_report_job,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph


def test_paid_report_full_generates_markdown_and_manifest() -> None:
    temp_dir = Path(".test_tmp") / f"reports-full-{uuid4().hex}"
    output_root = temp_dir / "outputs"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'reports.db'}")
        init_db()
        graph = build_mock_graph()
        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "legendary_gap_report")
            job = generate_report_job(
                session,
                graph,
                user_id="local-user",
                product_id="legendary_gap_report",
                goal_id="gw2:goal:aurora",
                export_format=ReportExportFormat.MARKDOWN,
                output_root=output_root,
            )

        artifact = Path(str(job.artifact_path))
        manifest = Path(str(job.manifest_path))
        assert job.status == "succeeded"
        assert artifact.exists()
        assert manifest.exists()
        assert "Missing Requirements" in artifact.read_text(encoding="utf-8")
        assert "no API keys" in artifact.read_text(encoding="utf-8")
        assert "Data Freshness & Source Confidence" in artifact.read_text(encoding="utf-8")
    finally:
        close_database()
