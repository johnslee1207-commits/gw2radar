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


class MissingCharactersPermissionGateway(DiagnosticAccountGateway):
    def _fetch_tokeninfo(self, api_key: str, *, request_id: str) -> dict:
        return {
            "name": "Missing Characters Test Key",
            "permissions": ["account", "inventories", "progression", "wallet"],
        }


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
        queue_check = next(check for check in before_payload["checks"] if check["check_id"] == "sync_job_visible")
        assert queue_check["status"] == "warn"
        assert queue_check["fix_action_id"] == "enqueueSync"
        assert queue_check["fix_label"] == "Sync now"
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


def test_account_debug_bundle_exports_privacy_safe_state_without_private_payloads() -> None:
    temp_dir = Path(".test_tmp") / f"account-debug-bundle-{uuid4().hex}"
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
        assert client.post("/api/v1/account/sync").status_code == 200
        assert client.post("/api/v1/account/sync/drain-one").status_code == 200
        response = client.post(
            "/account/debug-bundle",
            json={
                "active_view": "connect",
                "active_build_id": "build_secret_local_id",
                "player_intent": "build_fit",
                "report_history_count": 3,
            },
        )
        payload = response.json()
        rendered = str(payload)

        assert response.status_code == 200
        assert payload["schema_version"] == "gw2radar.account_debug_bundle.v1"
        assert payload["client_state"]["active_view"] == "connect"
        assert payload["client_state"]["active_build_id_present"] is True
        assert payload["client_state"]["report_history_count"] == 3
        assert payload["diagnostic_summary"]["summary_status"] == "ready"
        assert payload["snapshot_summary"]["synced_character_snapshot_count"] == 1
        assert payload["snapshot_summary"]["synced_gear_count"] >= 4
        assert CLEAN_KEY not in rendered
        assert "build_secret_local_id" not in rendered
        assert "Diagnostic Berserker Chest" not in rendered
        assert "Superior Rune of the Scholar" not in rendered
        assert "private item" in " ".join(payload["redaction_policy"]).lower()
    finally:
        account_route.permission_gateway_factory = original_permission_gateway
        account_sync_route.gateway_factory = original_sync_gateway
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_account_connection_diagnostic_names_missing_permission_and_fix_action() -> None:
    temp_dir = Path(".test_tmp") / f"account-diagnostic-permission-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    original_permission_gateway = account_route.permission_gateway_factory
    try:
        configure_database(f"sqlite:///{temp_dir / 'account.db'}")
        state.reset_cached_graph()
        account_route.permission_gateway_factory = MissingCharactersPermissionGateway
        client = TestClient(app)

        assert client.put("/account/api-key", json={"api_key": CLEAN_KEY}).status_code == 200
        payload = client.get("/account/diagnostic").json()
        permission_check = next(check for check in payload["checks"] if check["check_id"] == "permissions_ready")

        assert payload["summary_status"] == "blocked"
        assert permission_check["status"] == "fail"
        assert permission_check["severity"] == "critical"
        assert permission_check["fix_action_id"] == "focus_api_key_input"
        assert permission_check["fix_label"] == "Update key"
        assert "characters" in permission_check["details"]["missing_required_permissions"]
        assert "Missing required GW2 API key permissions: characters" in permission_check["player_message"]
        assert CLEAN_KEY not in str(payload)
    finally:
        account_route.permission_gateway_factory = original_permission_gateway
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
