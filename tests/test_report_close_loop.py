import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.config.settings import get_settings
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_report_close_loop_preview_license_generate_and_delivery_artifact() -> None:
    temp_dir = Path(".test_tmp") / f"report-close-loop-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'reports.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        catalog = client.get("/api/v1/reports/close-loop/catalog")
        preview = client.post(
            "/api/v1/reports/close-loop/preview",
            json={"product_id": "legendary_planner_pro_report", "goal_id": "gw2:goal:aurora"},
        )
        locked = client.post(
            "/api/v1/reports/close-loop/generate",
            json={"product_id": "legendary_planner_pro_report", "goal_id": "gw2:goal:aurora"},
        )
        grant = client.post(
            "/api/v1/reports/close-loop/mock-license",
            json={"product_id": "legendary_planner_pro_report"},
        )
        workflow = client.post(
            "/api/v1/reports/close-loop/workflow",
            json={
                "product_id": "legendary_planner_pro_report",
                "goal_id": "gw2:goal:aurora",
                "grant_mock_license": True,
            },
        )

        assert catalog.status_code == 200
        contracts = catalog.json()["data"]["contracts"]
        legendary_contract = next(
            contract for contract in contracts if contract["product_id"] == "legendary_planner_pro_report"
        )
        assert legendary_contract["preview_contract"]["requires_entitlement"] is False
        assert legendary_contract["full_report_contract"]["requires_entitlement"] is True
        assert legendary_contract["delivery_contract"]["shared_lifecycle"] is True
        assert legendary_contract["delivery_contract"]["productized_template_id"] == "legendary_gap_analysis"
        assert legendary_contract["entitlement_contract"]["payment_provider"] == "mock"
        assert legendary_contract["entitlement_contract"]["real_payment_provider_enabled"] is False

        assert preview.status_code == 200
        preview_payload = preview.json()["data"]["report_close_loop_preview"]
        preview_text = preview_payload["preview"]["preview"]
        assert "GW2Radar Free Report Preview" in preview_text
        assert "Missing Requirements" not in preview_text
        assert preview_payload["product_contract"]["full_report_contract"]["has_entitlement"] is False

        assert locked.status_code == 403
        assert grant.status_code == 200
        grant_payload = grant.json()["data"]["mock_license_grant"]
        assert grant_payload["payment_provider"] == "mock"
        assert grant_payload["granted"] is True

        assert workflow.status_code == 200
        workflow_payload = workflow.json()["data"]["report_close_loop_workflow"]
        generation = workflow_payload["generation"]
        assert generation["schema_version"] == "gw2radar.report_close_loop_full_generation.v1"
        assert generation["job"]["status"] == "succeeded"
        assert generation["delivery_artifact"]["schema_version"] == "gw2radar.productized_report_artifact.v1"
        assert generation["delivery_artifact"]["template_id"] == "legendary_gap_analysis"
        assert workflow_payload["readiness"]["entitled_product_count"] >= 1
        assert workflow_payload["readiness"]["full_report_job_count"] >= 1

        artifact_name = Path(generation["job"]["artifact_path"]).name
        artifact = client.get(f"/api/v1/reports/artifacts/{artifact_name}")
        assert artifact.status_code == 200
        assert "Commercial report mode: full" in artifact.text

        combined = str(catalog.json()) + str(preview.json()) + str(grant.json()) + str(workflow.json()) + artifact.text
        assert "secret-key" not in combined.lower()
        assert "guaranteed profit" not in combined.lower()
        assert "automatically buy" not in combined.lower()
        assert "automatically sell" not in combined.lower()
    finally:
        close_database()
        configure_database(get_settings().database_url)
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree("outputs", ignore_errors=True)
