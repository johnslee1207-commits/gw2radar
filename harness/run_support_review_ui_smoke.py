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
    audit_playbook = client.get("/account/debug-bundle/review/audit/playbook?reviewer=smoke&limit=10")
    audit_backlog = client.get("/account/debug-bundle/review/audit/backlog?reviewer=smoke&limit=10")
    backlog_markdown = client.get("/account/debug-bundle/review/audit/backlog?reviewer=smoke&format=markdown")
    backlog_csv = client.get("/account/debug-bundle/review/audit/backlog?reviewer=smoke&format=csv")
    promotion = client.post(
        "/account/debug-bundle/review/audit/backlog/promotions",
        json={
            "backlog_id": "support-backlog-frontend_flow_incomplete",
            "reviewer": "smoke",
            "audit_reviewer": "smoke",
        },
    )
    promotions = client.get("/account/debug-bundle/review/audit/backlog/promotions?reviewer=smoke")
    promotions_markdown = client.get("/account/debug-bundle/review/audit/backlog/promotions?reviewer=smoke&format=markdown")
    promotions_csv = client.get("/account/debug-bundle/review/audit/backlog/promotions?reviewer=smoke&format=csv")
    promotion_id = promotion.json().get("promotion", {}).get("promotion_id", "")
    promotion_status = client.post(
        f"/account/debug-bundle/review/audit/backlog/promotions/{promotion_id}/status",
        json={"status": "accepted", "reviewer": "smoke", "note": "Accepted during smoke."},
    )
    promotion_events = client.get(f"/account/debug-bundle/review/audit/backlog/promotions/events?promotion_id={promotion_id}")
    promotion_events_markdown = client.get(
        f"/account/debug-bundle/review/audit/backlog/promotions/events?promotion_id={promotion_id}&format=markdown"
    )
    promotion_events_csv = client.get(
        f"/account/debug-bundle/review/audit/backlog/promotions/events?promotion_id={promotion_id}&format=csv"
    )
    promotion_readiness = client.get("/account/debug-bundle/review/audit/backlog/promotions/readiness?audit_reviewer=smoke&promotion_reviewer=smoke")
    promotion_readiness_markdown = client.get(
        "/account/debug-bundle/review/audit/backlog/promotions/readiness?audit_reviewer=smoke&promotion_reviewer=smoke&format=markdown"
    )
    promotion_readiness_csv = client.get(
        "/account/debug-bundle/review/audit/backlog/promotions/readiness?audit_reviewer=smoke&promotion_reviewer=smoke&format=csv"
    )
    gateway_note = client.post(
        "/api/v1/player/gateway-incidents/review-notes",
        json={
            "status": "assigned",
            "reviewer": "smoke",
            "assignee": "ops",
            "note": "Support marked gateway incident for follow-up without requesting raw API keys.",
            "source": "support_smoke",
        },
    )
    gateway_notes = client.get("/api/v1/player/gateway-incidents/review-notes?reviewer=smoke&assignee=ops")
    gateway_notes_markdown = client.get("/api/v1/player/gateway-incidents/review-notes?reviewer=smoke&format=markdown")
    gateway_notes_csv = client.get("/api/v1/player/gateway-incidents/review-notes?reviewer=smoke&format=csv")
    gateway_note_id = gateway_note.json().get("data", {}).get("review_note", {}).get("note_id", "")
    gateway_note_closed = client.post(
        f"/api/v1/player/gateway-incidents/review-notes/{gateway_note_id}/status",
        json={"status": "closed", "reviewer": "smoke", "assignee": "ops", "note": "Closed during smoke."},
    )
    incident_dashboard = client.get("/api/v1/player/support-case/incident-dashboard?limit=20")
    incident_dashboard_markdown = client.get("/api/v1/player/support-case/incident-dashboard?format=markdown&limit=20")
    incident_dashboard_csv = client.get("/api/v1/player/support-case/incident-dashboard?format=csv&limit=20")

    _add(checks, "support page is served", page.status_code == 200 and "Debug Bundle Support Review" in page.text, page.text)
    _add(checks, "support script is served", js.status_code == 200 and "/account/debug-bundle/review" in js.text, js.text)
    _add(checks, "support styles are served", css.status_code == 200 and ".support-finding" in css.text, css.text)
    _add(checks, "support review API classifies sample flow", review.status_code == 200 and review.json().get("overall_status") == "frontend_flow_incomplete", review.text)
    _add(checks, "support audit stores safe review metadata", audit.status_code == 200 and audit.json().get("audit_record", {}).get("overall_status") == "frontend_flow_incomplete", audit.text)
    _add(checks, "support audit list exposes recent records", audit_list.status_code == 200 and len(audit_list.json().get("records", [])) >= 1, audit_list.text)
    _add(checks, "support audit filters recent records", audit_filtered.status_code == 200 and audit_filtered.json().get("filters", {}).get("reviewer") == "smoke", audit_filtered.text)
    _add(checks, "support audit exports privacy-safe csv", audit_csv.status_code == 200 and "text/csv" in audit_csv.headers.get("content-type", "") and "case_id,created_at,overall_status" in audit_csv.text, audit_csv.text)
    _add(checks, "support audit metrics summarize blockers", audit_metrics.status_code == 200 and audit_metrics.json().get("total_records", 0) >= 1 and audit_metrics.json().get("schema_version") == "gw2radar.account_debug_bundle_review_metrics.v1", audit_metrics.text)
    _add(checks, "support audit playbook maps blockers", audit_playbook.status_code == 200 and audit_playbook.json().get("schema_version") == "gw2radar.account_debug_bundle_review_playbook.v1" and audit_playbook.json().get("plays"), audit_playbook.text)
    _add(checks, "support audit backlog ranks product fixes", audit_backlog.status_code == 200 and audit_backlog.json().get("schema_version") == "gw2radar.account_debug_bundle_review_backlog.v1" and audit_backlog.json().get("backlog_items"), audit_backlog.text)
    _add(checks, "support audit backlog exports markdown", backlog_markdown.status_code == 200 and "# Support Review Product Backlog" in backlog_markdown.text, backlog_markdown.text)
    _add(checks, "support audit backlog exports csv", backlog_csv.status_code == 200 and "backlog_id,priority,blocker_id" in backlog_csv.text, backlog_csv.text)
    _add(checks, "support backlog promotes roadmap draft", promotion.status_code == 200 and promotion.json().get("status") == "created", promotion.text)
    _add(checks, "support backlog promotion list is visible", promotions.status_code == 200 and promotions.json().get("promotions"), promotions.text)
    _add(checks, "support backlog promotions export markdown", promotions_markdown.status_code == 200 and "# Support Backlog Promotion Drafts" in promotions_markdown.text, promotions_markdown.text)
    _add(checks, "support backlog promotions export csv", promotions_csv.status_code == 200 and "promotion_id,backlog_id,blocker_id" in promotions_csv.text, promotions_csv.text)
    _add(checks, "support backlog promotion status updates", promotion_status.status_code == 200 and promotion_status.json().get("status") == "updated", promotion_status.text)
    _add(checks, "support backlog promotion events are visible", promotion_events.status_code == 200 and len(promotion_events.json().get("events", [])) >= 2, promotion_events.text)
    _add(checks, "support backlog promotion events export markdown", promotion_events_markdown.status_code == 200 and "# Support Backlog Promotion Events" in promotion_events_markdown.text, promotion_events_markdown.text)
    _add(checks, "support backlog promotion events export csv", promotion_events_csv.status_code == 200 and "event_id,promotion_id,action" in promotion_events_csv.text, promotion_events_csv.text)
    _add(checks, "support promotion readiness rollup is visible", promotion_readiness.status_code == 200 and promotion_readiness.json().get("schema_version") == "gw2radar.support_promotion_readiness_rollup.v1", promotion_readiness.text)
    _add(checks, "support promotion readiness exports markdown", promotion_readiness_markdown.status_code == 200 and "# Support Promotion Readiness Rollup" in promotion_readiness_markdown.text, promotion_readiness_markdown.text)
    _add(checks, "support promotion readiness exports csv", promotion_readiness_csv.status_code == 200 and "ready,maturity_label,readiness_score" in promotion_readiness_csv.text, promotion_readiness_csv.text)
    _add(checks, "gateway incident notes UI controls are visible", "Incident Review Notes" in page.text and "saveGatewayIncidentNote" in js.text and "/api/v1/player/gateway-incidents/review-notes" in js.text, page.text + js.text)
    _add(checks, "gateway incident note stores workflow metadata", gateway_note.status_code == 200 and gateway_note.json().get("data", {}).get("review_note", {}).get("status") == "assigned", gateway_note.text)
    _add(checks, "gateway incident notes list filters metadata", gateway_notes.status_code == 200 and gateway_notes.json().get("data", {}).get("review_notes", {}).get("assigned_count", 0) >= 1, gateway_notes.text)
    _add(checks, "gateway incident notes export markdown", gateway_notes_markdown.status_code == 200 and "# Gateway Incident Review Notes" in gateway_notes_markdown.text, gateway_notes_markdown.text)
    _add(checks, "gateway incident notes export csv", gateway_notes_csv.status_code == 200 and "note_id,snapshot_id,status,reviewer,assignee" in gateway_notes_csv.text, gateway_notes_csv.text)
    _add(checks, "gateway incident note lifecycle closes metadata", gateway_note_closed.status_code == 200 and gateway_note_closed.json().get("data", {}).get("review_note", {}).get("status") == "closed", gateway_note_closed.text)
    _add(checks, "support case incident dashboard aggregates gates", incident_dashboard.status_code == 200 and incident_dashboard.json().get("data", {}).get("support_case_incident_dashboard", {}).get("schema_version") == "gw2radar.support_case_incident_dashboard.v1", incident_dashboard.text)
    _add(checks, "support case incident dashboard exports markdown", incident_dashboard_markdown.status_code == 200 and "# Support Case Incident Dashboard" in incident_dashboard_markdown.text, incident_dashboard_markdown.text)
    _add(checks, "support case incident dashboard exports csv", incident_dashboard_csv.status_code == 200 and "ready,maturity_label,support_status" in incident_dashboard_csv.text, incident_dashboard_csv.text)
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
