from pathlib import Path
from uuid import uuid4
import shutil

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.api.routes import account as account_route
from gw2radar.api.routes import account_sync as account_sync_route
from gw2radar.db.session import close_database, configure_database
from gw2radar.support.account_debug_bundle_review import review_account_debug_bundle
from harness.run_account_connection_diagnostic import CLEAN_KEY, DiagnosticAccountGateway


class MissingCharactersPermissionGateway(DiagnosticAccountGateway):
    def _fetch_tokeninfo(self, api_key: str, *, request_id: str) -> dict:
        return {
            "name": "Missing Characters Test Key",
            "permissions": ["account", "inventories", "progression", "wallet"],
        }


def test_support_review_detects_missing_required_permission_from_exported_bundle() -> None:
    temp_dir = Path(".test_tmp") / f"account-debug-review-permission-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    original_permission_gateway = account_route.permission_gateway_factory
    try:
        configure_database(f"sqlite:///{temp_dir / 'account.db'}")
        state.reset_cached_graph()
        account_route.permission_gateway_factory = MissingCharactersPermissionGateway
        client = TestClient(app)

        assert client.put("/account/api-key", json={"api_key": CLEAN_KEY}).status_code == 200
        bundle = client.post("/account/debug-bundle", json={"active_view": "connect"}).json()
        review = client.post("/account/debug-bundle/review", json=bundle).json()

        assert review["schema_version"] == "gw2radar.account_debug_bundle_review.v1"
        assert review["overall_status"] == "needs_permissions"
        assert review["bundle_schema_version"] == "gw2radar.account_debug_bundle.v1"
        assert review["findings"][0]["finding_id"] == "needs_permissions"
        assert "characters" in review["findings"][0]["player_message"]
        assert CLEAN_KEY not in str(review)
    finally:
        account_route.permission_gateway_factory = original_permission_gateway
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_support_review_detects_frontend_flow_incomplete_after_ready_backend() -> None:
    temp_dir = Path(".test_tmp") / f"account-debug-review-flow-{uuid4().hex}"
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
        bundle = client.post(
            "/account/debug-bundle",
            json={"active_view": "connect", "active_build_id": None, "player_intent": "build_fit"},
        ).json()
        review = review_account_debug_bundle(bundle)

        assert review.overall_status == "frontend_flow_incomplete"
        assert review.findings[0].finding_id == "frontend_flow_incomplete"
        assert "Build Fit" in review.findings[0].recommended_action
        assert CLEAN_KEY not in review.model_dump_json()
    finally:
        account_route.permission_gateway_factory = original_permission_gateway
        account_sync_route.gateway_factory = original_sync_gateway
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_support_review_rejects_sensitive_fields_in_bundle() -> None:
    bundle = {
        "schema_version": "gw2radar.account_debug_bundle.v1",
        "key_status": {"is_configured": True},
        "permission_summary": {"missing_required_permissions": []},
        "sync_summary": {"counts": {}},
        "diagnostic_summary": {"summary_status": "ready", "checks": []},
        "snapshot_summary": {"synced_character_snapshot_count": 1},
        "client_state": {"active_view": "build", "active_build_id_present": True},
        "api_key": "do-not-share",
    }

    review = review_account_debug_bundle(bundle)

    assert review.overall_status == "privacy_boundary_violation"
    assert review.findings[0].finding_id == "privacy_boundary_violation"
    assert "$.api_key" in review.findings[0].evidence_refs
    assert "do-not-share" not in review.model_dump_json()
