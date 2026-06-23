from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.ops.trial_defect_triage import (
    TrialDefectReport,
    build_trial_defect_dashboard,
    build_trial_readiness_checklist,
    render_trial_defect_dashboard_csv,
    render_trial_defect_dashboard_markdown,
    render_trial_readiness_checklist_markdown,
    triage_trial_defect,
)


def test_trial_readiness_checklist_exposes_real_user_entrypoints() -> None:
    checklist = build_trial_readiness_checklist()
    markdown = render_trial_readiness_checklist_markdown(checklist)

    assert checklist.schema_version == "gw2radar.trial_readiness_checklist.v1"
    assert checklist.status == "ready_for_user_trial"
    endpoints = {item.endpoint for item in checklist.checklist}
    assert "/account/diagnostic" in endpoints
    assert "/api/v1/ops/trial/defect-triage" in endpoints
    assert "Raw API keys are excluded" not in markdown
    assert "Never ask the player to send the raw key" in markdown


def test_trial_defect_triage_classifies_account_connection_empty_result_chain() -> None:
    cases = [
        (TrialDefectReport(symptom="pasted raw", raw_key_included=True), "raw_key_shared", False),
        (TrialDefectReport(symptom="no key"), "api_key_not_saved", True),
        (TrialDefectReport(symptom="missing perms", api_key_saved=True), "missing_permissions", True),
        (
            TrialDefectReport(symptom="not synced", api_key_saved=True, permissions_ready=True),
            "sync_not_started",
            True,
        ),
        (
            TrialDefectReport(symptom="sync pending", api_key_saved=True, permissions_ready=True, sync_queued=True),
            "sync_pending_or_failed",
            True,
        ),
        (
            TrialDefectReport(
                symptom="private empty",
                api_key_saved=True,
                permissions_ready=True,
                sync_queued=True,
                sync_succeeded=True,
            ),
            "private_layer_empty",
            True,
        ),
        (
            TrialDefectReport(
                symptom="character empty",
                api_key_saved=True,
                permissions_ready=True,
                sync_queued=True,
                sync_succeeded=True,
                private_snapshot_count=1,
            ),
            "character_snapshot_empty",
            True,
        ),
        (
            TrialDefectReport(
                symptom="result empty",
                api_key_saved=True,
                permissions_ready=True,
                sync_queued=True,
                sync_succeeded=True,
                private_snapshot_count=1,
                character_snapshot_count=1,
            ),
            "result_generation_empty",
            True,
        ),
        (
            TrialDefectReport(
                symptom="ui hidden",
                api_key_saved=True,
                permissions_ready=True,
                sync_queued=True,
                sync_succeeded=True,
                private_snapshot_count=1,
                character_snapshot_count=1,
                result_count=1,
            ),
            "ui_flow_incomplete",
            True,
        ),
    ]
    for report, expected, safe_to_store in cases:
        triage = triage_trial_defect(report)
        assert triage.classification == expected
        assert triage.safe_to_store is safe_to_store
        assert "raw API keys" in triage.boundary


def test_trial_defect_dashboard_exports_and_api_contract() -> None:
    dashboard = build_trial_defect_dashboard()
    markdown = render_trial_defect_dashboard_markdown(dashboard)
    csv = render_trial_defect_dashboard_csv(dashboard)
    client = TestClient(app)

    checklist_response = client.get("/api/v1/ops/trial/checklist")
    dashboard_response = client.get("/api/v1/ops/trial/defect-dashboard")
    dashboard_markdown = client.get("/api/v1/ops/trial/defect-dashboard?format=markdown")
    triage_response = client.post(
        "/api/v1/ops/trial/defect-triage",
        json={
            "symptom": "valid key but no output",
            "api_key_saved": True,
            "permissions_ready": True,
            "sync_queued": True,
            "sync_succeeded": True,
            "private_snapshot_count": 1,
            "character_snapshot_count": 1,
            "result_count": 0,
        },
    )

    assert dashboard.status == "ready_for_user_trial"
    assert "result_generation_empty" in dashboard.supported_classifications
    assert "# Trial Defect Triage Dashboard" in markdown
    assert "classification,status" in csv
    assert checklist_response.status_code == 200
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["data"]["trial_defect_dashboard"]["status"] == "ready_for_user_trial"
    assert dashboard_markdown.status_code == 200
    assert "# Trial Defect Triage Dashboard" in dashboard_markdown.text
    assert triage_response.status_code == 200
    assert triage_response.json()["data"]["trial_defect_triage"]["classification"] == "result_generation_empty"
