import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.db.session import close_database, configure_database


def test_support_review_audit_stores_safe_metadata_without_raw_bundle() -> None:
    temp_dir = Path(".test_tmp") / f"support-review-audit-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'support-review.db'}")
        state.reset_cached_graph()
        client = TestClient(app)
        bundle = _sample_bundle()
        raw_key_shaped_token = "12345678-1234-1234-1234-123456789abc-1234-1234-1234-123456789abc"

        response = client.post(
            "/account/debug-bundle/review/audit",
            json={
                "bundle": bundle,
                "reviewer": "support lead",
                "reply_template": f"Please do not send {raw_key_shaped_token}. Open Build Fit next.",
            },
        )
        payload = response.json()
        rendered = str(payload)

        assert response.status_code == 200
        assert payload["schema_version"] == "gw2radar.account_debug_bundle_review_audit_result.v1"
        assert payload["review"]["overall_status"] == "frontend_flow_incomplete"
        assert payload["audit_record"]["overall_status"] == "frontend_flow_incomplete"
        assert payload["audit_record"]["finding_ids"] == ["frontend_flow_incomplete"]
        assert payload["audit_record"]["properties"]["stores_raw_bundle"] is False
        assert payload["audit_record"]["properties"]["stores_raw_api_key"] is False
        assert "support lead" in payload["audit_record"]["reviewer"]
        assert raw_key_shaped_token not in rendered
        assert "Diagnostic Berserker Chest" not in rendered

        audit_list = client.get("/account/debug-bundle/review/audit?limit=5").json()

        assert audit_list["schema_version"] == "gw2radar.account_debug_bundle_review_audit_list.v1"
        assert len(audit_list["records"]) == 1
        assert audit_list["records"][0]["case_id"] == payload["audit_record"]["case_id"]
        assert raw_key_shaped_token not in str(audit_list)
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def _sample_bundle() -> dict:
    return {
        "schema_version": "gw2radar.account_debug_bundle.v1",
        "client_state": {"active_view": "connect", "active_build_id_present": False},
        "key_status": {"is_configured": True},
        "permission_summary": {"missing_required_permissions": []},
        "sync_summary": {"counts": {"retry_scheduled": 0}, "endpoint_progress": []},
        "diagnostic_summary": {
            "summary_status": "ready",
            "checks": [
                {"check_id": "api_key_stored", "status": "pass"},
                {"check_id": "permissions_ready", "status": "pass"},
                {"check_id": "sync_job_visible", "status": "pass"},
                {"check_id": "private_snapshot_written", "status": "pass"},
                {"check_id": "synced_character_snapshot", "status": "pass"},
                {"check_id": "build_fit_bridge_ready", "status": "pass"},
            ],
        },
        "snapshot_summary": {"synced_character_snapshot_count": 1, "synced_gear_count": 4},
        "debug_note": "Diagnostic Berserker Chest",
    }
