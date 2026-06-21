from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.report_engine import (
    create_report_entitlement,
    ensure_default_report_products,
    generate_report_job,
    generate_report_preview,
)
from gw2radar.commercial.market_radar import PriceSnapshotInput, record_price_snapshot
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph


def test_report_artifacts_do_not_leak_api_key_or_private_payload() -> None:
    temp_dir = Path(".test_tmp") / f"reports-secrets-{uuid4().hex}"
    secret = "12345678-1234-1234-1234-123456789abc"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'reports.db'}")
        init_db()
        graph = build_mock_graph()
        preview = generate_report_preview(graph, "gw2:goal:aurora", output_root=temp_dir / "outputs")
        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "legendary_gap_report")
            create_report_entitlement(session, "local-user", "build_fit_report")
            record_price_snapshot(
                session,
                PriceSnapshotInput(
                    item_id="gw2:item:mystic_coin",
                    item_name="Mystic Coin",
                    buy_price_copper=12000,
                    sell_price_copper=12500,
                    volume=10000,
                ),
            )
            job = generate_report_job(
                session,
                graph,
                user_id="local-user",
                product_id="legendary_gap_report",
                goal_id="gw2:goal:aurora",
                output_root=temp_dir / "outputs",
            )
            build_job = generate_report_job(
                session,
                graph,
                user_id="local-user",
                product_id="build_fit_report",
                goal_id="gw2:goal:aurora",
                output_root=temp_dir / "outputs",
            )

        combined = (
            str(preview["preview"])
            + Path(str(preview["manifest_path"])).read_text(encoding="utf-8")
            + Path(str(job.artifact_path)).read_text(encoding="utf-8")
            + Path(str(job.manifest_path)).read_text(encoding="utf-8")
            + Path(str(build_job.artifact_path)).read_text(encoding="utf-8")
            + Path(str(build_job.manifest_path)).read_text(encoding="utf-8")
        )
        assert secret not in combined
        assert "api_key" not in combined.lower()
        assert "raw private account payload" not in combined.lower()
        build_manifest = Path(str(build_job.manifest_path)).read_text(encoding="utf-8")
        assert '"account_value_snapshot"' in build_manifest
        assert '"evidence_bridge"' in build_manifest
        assert '"gw2radar.account_value_evidence_bridge.v1"' in build_manifest
        assert '"enabled": true' in build_manifest
        build_artifact = Path(str(build_job.artifact_path)).read_text(encoding="utf-8")
        assert "Account Value Snapshot" in build_artifact
        assert "Account Value Evidence Bridge" in build_artifact
    finally:
        close_database()
