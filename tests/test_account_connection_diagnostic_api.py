import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.api.routes import account as account_route
from gw2radar.api.routes import account_sync as account_sync_route
from gw2radar.db.session import close_database, configure_database
from harness.run_account_connection_diagnostic import CLEAN_KEY, DiagnosticAccountGateway


def test_account_connection_diagnostic_reports_sync_and_build_fit_bridge_without_key_leakage() -> None:
    temp_dir = Path(".test_tmp") / f"account-diagnostic-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    original_permission_gateway = account_route.permission_gateway_factory
    original_sync_gateway = account_sync_route.gateway_factory
    try:
        configure_database(f"sqlite:///{temp_dir / 'account.db'}")
        state.reset_cached_graph()
        account_route.permission_gateway_factory = DiagnosticAccountGateway
        account_sync_route.gateway_factory = DiagnosticAccountGateway
        client = TestClient(app)

        assert client.put("/account/api-key", json={"api_key": CLEAN_KEY}).status_code == 200
        before_sync = client.get("/account/diagnostic")
        assert before_sync.status_code == 200
        before_payload = before_sync.json()
        assert before_payload["schema_version"] == "gw2radar.account_connection_diagnostic.v1"
        assert before_payload["summary_status"] == "needs_sync"
        assert before_payload["snapshot_summary"]["synced_character_snapshot_count"] == 0
        assert CLEAN_KEY not in str(before_payload)

        assert client.post("/api/v1/account/sync").status_code == 200
        assert client.post("/api/v1/account/sync/drain-one").status_code == 200
        after_sync = client.get("/account/diagnostic")
        after_payload = after_sync.json()

        assert after_sync.status_code == 200
        assert after_payload["summary_status"] == "ready"
        assert {check["status"] for check in after_payload["checks"]} == {"pass"}
        assert after_payload["snapshot_summary"]["private_player_state_count"] >= 5
        assert after_payload["snapshot_summary"]["synced_character_snapshot_count"] == 1
        assert after_payload["snapshot_summary"]["synced_gear_count"] >= 4
        assert "Raw API keys" in after_payload["boundary"]
        assert CLEAN_KEY not in str(after_payload)
    finally:
        account_route.permission_gateway_factory = original_permission_gateway
        account_sync_route.gateway_factory = original_sync_gateway
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
