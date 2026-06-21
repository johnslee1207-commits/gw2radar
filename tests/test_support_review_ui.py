from fastapi.testclient import TestClient

from gw2radar.api.main import app


client = TestClient(app)


def test_support_review_page_serves_operator_workbench() -> None:
    response = client.get("/support")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Debug Bundle Support Review" in response.text
    assert "Load Debug Bundle" in response.text
    assert "Support Decision" in response.text
    assert "Player reply template" in response.text
    assert "Recent Review Records" in response.text
    assert "Save audit" in response.text
    assert "Export CSV" in response.text
    assert "Failure Reason Summary" in response.text
    assert "Refresh metrics" in response.text
    assert "Remediation Steps" in response.text
    assert "Refresh playbook" in response.text
    assert "Product Fix Backlog" in response.text
    assert "Refresh backlog" in response.text
    assert "Export MD" in response.text
    assert "Roadmap Drafts" in response.text
    assert "Refresh drafts" in response.text
    assert "promotion-list" in response.text
    assert "Promotion Events" in response.text
    assert "Refresh events" in response.text
    assert "promotion-event-list" in response.text
    assert "Promotion Readiness" in response.text
    assert "Refresh readiness" in response.text
    assert "promotion-readiness-summary" in response.text
    assert "Incident Review Notes" in response.text
    assert "gateway-note-summary" in response.text
    assert "Save note" in response.text
    assert "audit-severity-filter" in response.text
    assert "Do Not Request Secrets" in response.text
    assert "Do not ask for a raw GW2 API key" in response.text
    assert "/player-ui/support.js" in response.text


def test_support_review_static_assets_include_review_workflow() -> None:
    js = client.get("/player-ui/support.js")
    css = client.get("/player-ui/styles.css")

    assert js.status_code == 200
    assert "/account/debug-bundle/review" in js.text
    assert "/account/debug-bundle/review/audit" in js.text
    assert "buildReplyTemplate" in js.text
    assert "saveAuditRecord" in js.text
    assert "renderAuditRecords" in js.text
    assert "auditQueryString" in js.text
    assert "exportAuditCsv" in js.text
    assert "/account/debug-bundle/review/audit/metrics" in js.text
    assert "/account/debug-bundle/review/audit/playbook" in js.text
    assert "/account/debug-bundle/review/audit/backlog" in js.text
    assert "renderAuditMetrics" in js.text
    assert "renderMetricList" in js.text
    assert "renderPlaybook" in js.text
    assert "renderBacklog" in js.text
    assert "exportBacklog" in js.text
    assert "promoteBacklogItem" in js.text
    assert "renderPromotions" in js.text
    assert "updatePromotionStatus" in js.text
    assert "renderPromotionEvents" in js.text
    assert "promotionEventQueryString" in js.text
    assert "renderPromotionReadiness" in js.text
    assert "promotionReadinessQueryString" in js.text
    assert "saveGatewayIncidentNote" in js.text
    assert "refreshGatewayIncidentNotes" in js.text
    assert "renderGatewayIncidentNotes" in js.text
    assert "updateGatewayIncidentNoteStatus" in js.text
    assert "Defer" in js.text
    assert "/api/v1/player/gateway-incidents/review-notes" in js.text
    assert "/account/debug-bundle/review/audit/backlog/promotions" in js.text
    assert "/account/debug-bundle/review/audit/backlog/promotions/events" in js.text
    assert "/account/debug-bundle/review/audit/backlog/promotions/readiness" in js.text
    assert "Promote draft" in js.text
    assert "Mark linked" in js.text
    assert "markdown" in js.text
    assert 'params.set("format", format)' in js.text
    assert "privacy-boundary violations" not in js.text
    assert "Please do not send your raw GW2 API key" in js.text
    assert "navigator.clipboard.writeText" in js.text
    assert css.status_code == 200
    assert ".support-grid" in css.text
    assert ".support-finding.critical" in css.text
    assert ".support-audit-record.critical" in css.text
    assert ".support-metrics-grid" in css.text
    assert ".support-playbook-item" in css.text
    assert ".support-backlog-item" in css.text
    assert ".support-promotion-item" in css.text
    assert ".support-finding.warning" in css.text
    assert ".support-finding.info" in css.text


def test_support_review_api_contract_matches_ui_sample() -> None:
    response = client.post("/account/debug-bundle/review", json=_ui_sample_bundle())
    payload = response.json()

    assert response.status_code == 200
    assert payload["schema_version"] == "gw2radar.account_debug_bundle_review.v1"
    assert payload["overall_status"] == "frontend_flow_incomplete"
    assert payload["findings"][0]["finding_id"] == "frontend_flow_incomplete"
    assert "Build Fit" in payload["findings"][0]["recommended_action"]


def _ui_sample_bundle() -> dict:
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
