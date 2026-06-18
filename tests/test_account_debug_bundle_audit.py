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


def test_support_review_audit_filters_and_exports_privacy_safe_csv() -> None:
    temp_dir = Path(".test_tmp") / f"support-review-audit-filter-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'support-review-filter.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        ready = client.post(
            "/account/debug-bundle/review/audit",
            json={"bundle": _ready_bundle(), "reviewer": "alice", "reply_template": "Ready flow."},
        ).json()
        critical = client.post(
            "/account/debug-bundle/review/audit",
            json={"bundle": _missing_key_bundle(), "reviewer": "bob", "reply_template": "Paste a key."},
        ).json()

        assert ready["audit_record"]["overall_status"] == "ready"
        assert critical["audit_record"]["highest_severity"] == "critical"

        filtered = client.get("/account/debug-bundle/review/audit?severity=critical&reviewer=bob&limit=10").json()

        assert filtered["filters"]["severity"] == "critical"
        assert filtered["filters"]["reviewer"] == "bob"
        assert len(filtered["records"]) == 1
        assert filtered["records"][0]["case_id"] == critical["audit_record"]["case_id"]

        csv_response = client.get("/account/debug-bundle/review/audit?status=ready&format=csv")
        csv_text = csv_response.text

        assert csv_response.status_code == 200
        assert "text/csv" in csv_response.headers["content-type"]
        assert "case_id,created_at,overall_status" in csv_text
        assert ready["audit_record"]["case_id"] in csv_text
        assert critical["audit_record"]["case_id"] not in csv_text
        assert "Diagnostic Berserker Chest" not in csv_text
        assert "debug_note" not in csv_text
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_support_review_audit_metrics_summarize_top_blockers() -> None:
    temp_dir = Path(".test_tmp") / f"support-review-audit-metrics-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'support-review-metrics.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        client.post("/account/debug-bundle/review/audit", json={"bundle": _ready_bundle(), "reviewer": "metrics"})
        client.post("/account/debug-bundle/review/audit", json={"bundle": _missing_key_bundle(), "reviewer": "metrics"})
        client.post("/account/debug-bundle/review/audit", json={"bundle": _missing_permission_bundle(), "reviewer": "metrics"})

        metrics = client.get("/account/debug-bundle/review/audit/metrics?reviewer=metrics&limit=10").json()
        rendered = str(metrics)

        assert metrics["schema_version"] == "gw2radar.account_debug_bundle_review_metrics.v1"
        assert metrics["total_records"] == 3
        assert _count_for(metrics["status_counts"], "ready") == 1
        assert _count_for(metrics["status_counts"], "needs_key") == 1
        assert _count_for(metrics["status_counts"], "needs_permissions") == 1
        assert _count_for(metrics["severity_counts"], "critical") == 2
        assert _count_for(metrics["finding_counts"], "needs_key") == 1
        assert _count_for(metrics["finding_counts"], "needs_permissions") == 1
        assert metrics["top_blockers"][0]["count"] == 1
        assert "privacy-safe audit metadata" in metrics["boundary"]
        assert "Diagnostic Berserker Chest" not in rendered
        assert "diagnostic_summary" not in rendered
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


def _ready_bundle() -> dict:
    bundle = _sample_bundle()
    bundle["client_state"] = {"active_view": "build", "active_build_id_present": True}
    bundle.pop("debug_note", None)
    return bundle


def _missing_key_bundle() -> dict:
    bundle = _sample_bundle()
    bundle["key_status"] = {"is_configured": False}
    bundle["diagnostic_summary"]["summary_status"] = "blocked"
    bundle["diagnostic_summary"]["checks"][0] = {"check_id": "api_key_stored", "status": "fail"}
    bundle.pop("debug_note", None)
    return bundle


def _missing_permission_bundle() -> dict:
    bundle = _sample_bundle()
    bundle["permission_summary"] = {"missing_required_permissions": ["characters"]}
    bundle["diagnostic_summary"]["summary_status"] = "blocked"
    bundle["diagnostic_summary"]["checks"][1] = {"check_id": "permissions_ready", "status": "fail"}
    bundle.pop("debug_note", None)
    return bundle


def _count_for(counts: list[dict], key: str) -> int:
    return next((item["count"] for item in counts if item["key"] == key), 0)
