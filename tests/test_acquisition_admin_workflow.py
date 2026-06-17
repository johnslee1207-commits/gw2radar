from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.api.routes import acquisition as acquisition_route
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.acquisition.repository import mark_job_succeeded


def test_acquisition_admin_workflow_creates_reviews_enqueues_drains_and_exports(monkeypatch) -> None:
    temp_dir = Path(".test_tmp") / f"acq-admin-flow-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        client = TestClient(app)

        class FakeWorker:
            def __init__(self, session, *, api_key_provider=None):
                self.session = session

            def drain_one(self, worker_id="acquisition-admin-workflow"):
                jobs = acquisition_route.list_jobs(self.session, status=acquisition_route.AcquisitionJobStatus.QUEUED)
                job = mark_job_succeeded(self.session, jobs[0].job_id)
                return {
                    "status": "succeeded",
                    "job_id": job.job_id,
                    "source_id": job.source_id,
                    "gateway_status": "ok",
                    "evidence_created": False,
                }

        monkeypatch.setattr(acquisition_route, "AcquisitionWorker", FakeWorker)

        created = client.post(
            "/api/v1/acquisition/admin/workflow",
            json={
                "source": {
                    "name": "Official Items API",
                    "source_type": "official_api_public",
                    "acquisition_mode": "api",
                    "base_url": "https://api.guildwars2.com",
                    "allowed_use": "api_json",
                    "graph_target": "public_game",
                    "kb_target": "official",
                    "review_required": False,
                },
                "policy": {
                    "allowed_use": "api_json",
                    "refresh_mode": "scheduled",
                    "refresh_interval_seconds": 3600,
                    "can_drive_paid_report": True,
                    "can_drive_strong_recommendation": True,
                },
                "mark_reviewed": True,
                "include_readiness": True,
            },
        )
        source_id = created.json()["data"]["steps"][0]["source"]["source_id"]
        run = client.post(
            "/api/v1/acquisition/admin/workflow",
            json={
                "source_id": source_id,
                "job": {
                    "source_id": source_id,
                    "params": {"endpoint": "/v2/items", "request_params": {"ids": [19721]}},
                },
                "drain_one": True,
                "use_stored_api_key": False,
                "include_readiness": True,
                "include_markdown_export": True,
            },
        )

        assert created.status_code == 200
        assert [step["step"] for step in created.json()["data"]["steps"]] == [
            "source_created",
            "policy_upserted",
            "source_reviewed",
        ]
        assert run.status_code == 200
        run_data = run.json()["data"]
        assert [step["step"] for step in run_data["steps"]] == ["job_created", "drain_one"]
        assert run_data["steps"][1]["result"]["status"] == "succeeded"
        assert run_data["readiness"]["paid_report_source_count"] == 1
        assert "# Acquisition Readiness" in run_data["readiness_markdown"]
        assert "12345678-abcdef-secret-key" not in str(run_data)
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_acquisition_admin_workflow_rejects_conflicting_source_actions() -> None:
    temp_dir = Path(".test_tmp") / f"acq-admin-conflict-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        response = TestClient(app).post(
            "/api/v1/acquisition/admin/workflow",
            json={"source_id": "missing", "mark_reviewed": True, "mark_deprecated": True},
        )

        assert response.status_code == 400
        assert "reviewed and deprecated" in response.json()["error"]["message"]
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_acquisition_admin_workflow_rejects_job_source_mismatch() -> None:
    temp_dir = Path(".test_tmp") / f"acq-admin-mismatch-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        response = TestClient(app).post(
            "/api/v1/acquisition/admin/workflow",
            json={
                "source_id": "source_a",
                "job": {"source_id": "source_b", "params": {"endpoint": "/v2/items"}},
            },
        )

        assert response.status_code == 400
        assert "job.source_id" in response.json()["error"]["message"]
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)
