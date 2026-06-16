import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.commercial.report_engine import create_report_entitlement, ensure_default_report_products
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_paid_report_api_routes_preview_generate_status_and_artifact() -> None:
    temp_dir = Path(".test_tmp") / f"reports-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'reports.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        products = client.get("/api/v1/reports/products")
        preview = client.post("/api/v1/reports/preview", json={"goal_id": "gw2:goal:aurora"})
        locked = client.post(
            "/api/v1/reports/generate",
            json={"product_id": "legendary_gap_report", "goal_id": "gw2:goal:aurora"},
        )

        assert products.status_code == 200
        assert preview.status_code == 200
        assert locked.status_code == 403
        assert "Missing Requirements" not in preview.json()["data"]["preview"]

        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "legendary_gap_report")

        generated = client.post(
            "/api/v1/reports/generate",
            json={"product_id": "legendary_gap_report", "goal_id": "gw2:goal:aurora"},
        )
        assert generated.status_code == 200
        job = generated.json()["data"]["job"]
        status = client.get(f"/api/v1/reports/jobs/{job['job_id']}")
        artifact_name = Path(job["artifact_path"]).name
        artifact = client.get(f"/api/v1/reports/artifacts/{artifact_name}")

        assert status.status_code == 200
        assert status.json()["data"]["job"]["status"] == "succeeded"
        assert artifact.status_code == 200
        assert "Missing Requirements" in artifact.text
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree("outputs", ignore_errors=True)
