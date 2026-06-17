from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_acquisition_api_source_policy_health_and_job_flow() -> None:
    temp_dir = Path(".test_tmp") / f"acq-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'acquisition.db'}")
        init_db()
        client = TestClient(app)

        created = client.post(
            "/api/v1/sources",
            json={
                "name": "Official Patch PDFs",
                "source_type": "downloaded_pdf",
                "acquisition_mode": "local_file",
                "local_path": "docs/knowledge_base/_sources/pdf/news",
                "allowed_use": "summary_and_reference",
                "graph_target": "public_game",
                "kb_target": "official",
                "trust_level": 0.9,
            },
        )
        assert created.status_code == 200
        source_id = created.json()["data"]["source"]["source_id"]

        listed = client.get("/api/v1/sources", params={"kb_target": "official"})
        reviewed = client.post(f"/api/v1/sources/{source_id}/mark-reviewed")
        policy = client.post(
            f"/api/v1/sources/{source_id}/policy",
            json={
                "allowed_use": "summary_and_reference",
                "refresh_mode": "manual",
                "can_drive_paid_report": True,
                "can_drive_strong_recommendation": False,
                "forbidden_use": ["full_text_copy", "automated_trade"],
            },
        )
        job = client.post(
            "/api/v1/acquisition/jobs",
            json={"source_id": source_id, "params": {"year": 2026}, "requested_by": "test"},
        )
        job_id = job.json()["data"]["job"]["job_id"]
        skipped = client.post(f"/api/v1/acquisition/jobs/{job_id}/run-once")
        health = client.get(f"/api/v1/sources/{source_id}/health")

        assert listed.status_code == 200
        assert listed.json()["data"]["sources"][0]["source_id"] == source_id
        assert reviewed.status_code == 200
        assert policy.status_code == 200
        assert job.status_code == 200
        assert skipped.status_code == 200
        assert skipped.json()["data"]["job"]["status"] == "skipped"
        assert skipped.json()["data"]["job"]["last_error_code"] == "adapter_not_implemented"
        assert health.status_code == 200
        assert health.json()["data"]["health"]["freshness_status"] == "unknown"
    finally:
        close_database()
