import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.commercial.report_engine import create_report_entitlement, ensure_default_report_products
from gw2radar.config.settings import get_settings
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_productized_report_templates_generate_artifacts_and_preserve_boundaries() -> None:
    temp_dir = Path(".test_tmp") / f"productized-reports-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'reports.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        templates = client.get("/api/v1/reports/productized/templates")
        assert templates.status_code == 200
        template_payload = templates.json()["data"]["templates"]
        assert {template["template_id"] for template in template_payload} == {
            "account_value_analysis",
            "legendary_gap_analysis",
            "build_readiness_advisor",
        }
        assert all("csv" in template["export_formats"] for template in template_payload)

        locked = client.post(
            "/api/v1/reports/productized/generate",
            json={"template_id": "account_value_analysis", "format": "markdown"},
        )
        assert locked.status_code == 403

        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "account_value_report")
            create_report_entitlement(session, "local-user", "legendary_planner_pro_report")
            create_report_entitlement(session, "local-user", "build_fit_report")

        account_report = client.post(
            "/api/v1/reports/productized/generate",
            json={"template_id": "account_value_analysis", "format": "markdown"},
        )
        legendary_report = client.post(
            "/api/v1/reports/productized/generate",
            json={"template_id": "legendary_gap_analysis", "format": "csv"},
        )
        build_report = client.post(
            "/api/v1/reports/productized/generate",
            json={"template_id": "build_readiness_advisor", "format": "html"},
        )

        assert account_report.status_code == 200
        assert legendary_report.status_code == 200
        assert build_report.status_code == 200
        account_manifest = account_report.json()["data"]["productized_report"]
        legendary_manifest = legendary_report.json()["data"]["productized_report"]
        build_manifest = build_report.json()["data"]["productized_report"]

        assert account_manifest["schema_version"] == "gw2radar.productized_report_artifact.v1"
        assert account_manifest["product_id"] == "account_value_report"
        assert account_manifest["format"] == "markdown"
        assert "Account Value Snapshot" in account_manifest["sections"]
        assert len(account_manifest["checksum_sha256"]) == 64
        assert legendary_manifest["format"] == "csv"
        assert "Do-Not-Sell List" in legendary_manifest["sections"]
        assert build_manifest["format"] == "html"
        assert "Transition Plan" in build_manifest["sections"]

        account_artifact = client.get(f"/api/v1/reports/artifacts/{Path(account_manifest['artifact_path']).name}")
        legendary_artifact = client.get(f"/api/v1/reports/artifacts/{Path(legendary_manifest['artifact_path']).name}")
        build_artifact = client.get(f"/api/v1/reports/artifacts/{Path(build_manifest['artifact_path']).name}")

        assert account_artifact.status_code == 200
        assert "# Account Value Analysis Report" in account_artifact.text
        assert "Account Value Snapshot" in account_artifact.text
        assert legendary_artifact.status_code == 200
        assert "row_type,entity_id,name,quantity,detail" in legendary_artifact.text
        assert build_artifact.status_code == 200
        assert "<!doctype html>" in build_artifact.text
        assert "Build Readiness And Gear Transition Report" in build_artifact.text

        combined = (
            str(account_manifest)
            + str(legendary_manifest)
            + str(build_manifest)
            + account_artifact.text
            + legendary_artifact.text
            + build_artifact.text
        ).lower()
        assert "secret-key" not in combined
        assert "private_source_payload" not in combined
        assert "manual player review" in account_manifest["manual_action_boundary"]
    finally:
        close_database()
        configure_database(get_settings().database_url)
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree("outputs", ignore_errors=True)
