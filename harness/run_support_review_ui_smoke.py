"""Support review UI smoke harness."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gw2radar.api.main import app  # noqa: E402


def main() -> int:
    client = TestClient(app)
    checks: list[tuple[str, bool, str]] = []

    page = client.get("/support")
    js = client.get("/player-ui/support.js")
    css = client.get("/player-ui/styles.css")
    review = client.post("/account/debug-bundle/review", json=_sample_bundle())
    audit = client.post(
        "/account/debug-bundle/review/audit",
        json={"bundle": _sample_bundle(), "reviewer": "smoke", "reply_template": "Open Build Fit next."},
    )
    audit_list = client.get("/account/debug-bundle/review/audit?limit=3")
    audit_filtered = client.get("/account/debug-bundle/review/audit?severity=info&reviewer=smoke&limit=3")
    audit_csv = client.get("/account/debug-bundle/review/audit?severity=info&reviewer=smoke&format=csv")
    audit_metrics = client.get("/account/debug-bundle/review/audit/metrics?reviewer=smoke&limit=10")

    _add(checks, "support page is served", page.status_code == 200 and "Debug Bundle Support Review" in page.text, page.text)
    _add(checks, "support script is served", js.status_code == 200 and "/account/debug-bundle/review" in js.text, js.text)
    _add(checks, "support styles are served", css.status_code == 200 and ".support-finding" in css.text, css.text)
    _add(checks, "support review API classifies sample flow", review.status_code == 200 and review.json().get("overall_status") == "frontend_flow_incomplete", review.text)
    _add(checks, "support audit stores safe review metadata", audit.status_code == 200 and audit.json().get("audit_record", {}).get("overall_status") == "frontend_flow_incomplete", audit.text)
    _add(checks, "support audit list exposes recent records", audit_list.status_code == 200 and len(audit_list.json().get("records", [])) >= 1, audit_list.text)
    _add(checks, "support audit filters recent records", audit_filtered.status_code == 200 and audit_filtered.json().get("filters", {}).get("reviewer") == "smoke", audit_filtered.text)
    _add(checks, "support audit exports privacy-safe csv", audit_csv.status_code == 200 and "text/csv" in audit_csv.headers.get("content-type", "") and "case_id,created_at,overall_status" in audit_csv.text, audit_csv.text)
    _add(checks, "support audit metrics summarize blockers", audit_metrics.status_code == 200 and audit_metrics.json().get("total_records", 0) >= 1 and audit_metrics.json().get("schema_version") == "gw2radar.account_debug_bundle_review_metrics.v1", audit_metrics.text)
    _add(checks, "no-secret boundary is visible", "Do not ask for a raw GW2 API key" in page.text and "Please do not send your raw GW2 API key" in js.text, "boundary missing")

    failed = [check for check in checks if not check[1]]
    for name, passed, detail in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {name}")
        if not passed:
            print(f"  detail: {detail[:400]}")
    if failed:
        print("FAIL: GW2Radar support review UI smoke failed")
        return 1
    print("PASS: GW2Radar support review UI smoke succeeded")
    return 0


def _add(checks: list[tuple[str, bool, str]], name: str, passed: bool, detail: str) -> None:
    checks.append((name, passed, detail))


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
    }


if __name__ == "__main__":
    raise SystemExit(main())
