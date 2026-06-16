from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.db.session import close_database, configure_database
from harness import run_sync_smoke


def test_http_errors_use_uniform_error_envelope() -> None:
    temp_dir = Path(".test_tmp") / f"error-envelope-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        state.reset_cached_graph()
        response = TestClient(app).get("/goals/not-a-goal/gap")

        assert response.status_code == 404
        assert response.json() == {
            "ok": False,
            "error": {
                "code": "not_found",
                "message": "Goal not found",
                "details": {"path": "/goals/not-a-goal/gap"},
            },
        }
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_operational_status_summary_endpoint() -> None:
    temp_dir = Path(".test_tmp") / f"ops-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'ops.db'}")
        state.reset_cached_graph()
        client = TestClient(app)
        response = client.get("/api/v1/ops/status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["ok"] is True
        assert payload["data"]["status"] == "ok"
        assert payload["data"]["database"] == "ok"
        assert payload["data"]["capabilities"]["account_sync"] is True
        assert payload["data"]["capabilities"]["public_refresh"] is True
        assert "entities" in payload["data"]["graph"]
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_fake_gateway_sync_smoke_harness_passes() -> None:
    assert run_sync_smoke.main() == 0
