import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.db.session import close_database, configure_database


client = TestClient(app)


def test_player_os_intent_api_and_plan_revision_flow() -> None:
    parsed = client.post("/api/v1/intents/parse", json={"raw_text": "我想做 Aurora，尽量少花金币，不想打 WvW。"})
    assert parsed.status_code == 200
    assert parsed.json()["data"]["intent_parse"]["intent"]["intent_type"] == "legendary"

    started = client.post("/api/v1/intents/start", json={"raw_text": "Can I play Open World Power Reaper with 50 gold?"})
    assert started.status_code == 200
    payload = started.json()["data"]["intent_start"]
    plan_id = payload["plan"]["plan_id"]
    workflow_id = payload["workflow"]["workflow_id"]
    report_id = payload["report_preview"]["report_id"]

    assert payload["workflow"]["workflow_type"] == "build_fit_wizard"
    assert payload["governance"]["status"] == "ready"

    workflow = client.post(f"/api/v1/workflows/{workflow_id}/answer", json={"answer": {"build_id": "sample"}})
    assert workflow.status_code == 200
    assert workflow.json()["data"]["workflow"]["status"] == "planning"

    revised = client.post(f"/api/v1/plans/{plan_id}/revise", json={"raw_revision_text": "I only have 30 minutes per day."})
    assert revised.status_code == 200
    assert revised.json()["data"]["diff"]["changed_constraints"]["daily_time_limit"] == "30m"

    what_if = client.post(f"/api/v1/plans/{plan_id}/what-if", json={"raw_text": "What if I avoid WvW?"})
    assert what_if.status_code == 200
    assert what_if.json()["data"]["what_if"]["changed_constraints"]["avoid_modes"] == ["wvw"]

    report = client.post(f"/api/v1/reports/{report_id}/revise", json={"raw_revision_text": "Use cheaper route."})
    assert report.status_code == 200
    assert report.json()["data"]["report"]["version"] == 2


def test_player_os_templates_now_and_pages() -> None:
    templates = client.get("/api/v1/templates")
    assert templates.status_code == 200
    assert any(item["template_id"] == "account.what_should_i_do_now" for item in templates.json()["data"]["templates"])

    started = client.post("/api/v1/templates/account.what_should_i_do_now/start")
    assert started.status_code == 200
    assert started.json()["data"]["intent_start"]["plan"]["title"] == "What Should I Do Now?"

    now = client.get("/api/v1/now")
    assert now.status_code == 200
    assert now.json()["data"]["now"]["top_actions"]

    for path in ["/start", "/now", "/templates", "/help", "/wizard/returner", "/plan/revise", "/report/revise"]:
        response = client.get(path)
        assert response.status_code == 200
        assert "GW2Radar Player OS" in response.text
        assert "/api/v1/intents/start" in response.text


def test_player_os_trial_feedback_review_classifies_ready_but_empty_result() -> None:
    response = client.post(
        "/api/v1/player-os/trial-feedback/review",
        json={"feedback": _trial_feedback(ready=True)},
    )

    assert response.status_code == 200
    review = response.json()["data"]["trial_feedback_review"]
    assert review["schema_version"] == "gw2radar.player_os_trial_feedback_review.v1"
    assert review["overall_status"] == "result_generation_empty"
    assert review["ready_gate_count"] == 5
    assert review["last_bridge_target"] == "legendary"
    assert review["findings"][0]["finding_id"] == "result_generation_empty"
    assert "raw GW2 API key" in review["player_reply_template"]


def test_player_os_trial_feedback_review_flags_incomplete_deep_link() -> None:
    response = client.post(
        "/api/v1/player-os/trial-feedback/review",
        json={"feedback": _trial_feedback(ready=False, missing_row="deep_link")},
    )

    assert response.status_code == 200
    review = response.json()["data"]["trial_feedback_review"]
    assert review["overall_status"] == "deep_link_not_opened"
    assert "checklist.rows.deep_link" in review["findings"][0]["evidence_refs"]
    assert review["operator_next_actions"]


def test_player_os_trial_feedback_review_blocks_sensitive_fields() -> None:
    feedback = _trial_feedback(ready=True)
    feedback["raw_key"] = "do-not-store"
    response = client.post("/api/v1/player-os/trial-feedback/review", json={"feedback": feedback})

    assert response.status_code == 200
    review = response.json()["data"]["trial_feedback_review"]
    assert review["overall_status"] == "privacy_boundary_violation"
    assert review["findings"][0]["severity"] == "critical"


def test_player_os_trial_feedback_audit_feeds_metrics_and_backlog() -> None:
    temp_dir = Path(".test_tmp") / f"player-os-trial-feedback-audit-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'trial-feedback.db'}")
        state.reset_cached_graph()
        local_client = TestClient(app)
        feedback = _trial_feedback(ready=False, missing_row="deep_link")

        saved = local_client.post(
            "/api/v1/player-os/trial-feedback/review/audit",
            json={"feedback": feedback, "reviewer": "trial-support"},
        )
        assert saved.status_code == 200
        saved_payload = saved.json()["data"]
        assert saved_payload["trial_feedback_review"]["overall_status"] == "deep_link_not_opened"
        record = saved_payload["trial_feedback_audit_record"]
        assert record["source"] == "player_os_trial_feedback"
        assert record["properties"]["stores_raw_feedback"] is False
        assert record["properties"]["stores_raw_api_key"] is False
        assert "raw_key" not in str(record)

        listed = local_client.get("/api/v1/player-os/trial-feedback/review/audit?reviewer=trial-support")
        assert listed.status_code == 200
        assert listed.json()["data"]["trial_feedback_audit"]["records"][0]["overall_status"] == "deep_link_not_opened"

        metrics = local_client.get("/api/v1/player-os/trial-feedback/review/audit/metrics?reviewer=trial-support")
        assert metrics.status_code == 200
        metrics_payload = metrics.json()["data"]["trial_feedback_metrics"]
        assert metrics_payload["schema_version"] == "gw2radar.player_os_trial_feedback_metrics.v1"
        assert metrics_payload["total_records"] == 1
        assert metrics_payload["top_blockers"][0]["key"] == "deep_link_not_opened"

        backlog = local_client.get("/api/v1/player-os/trial-feedback/review/audit/backlog?reviewer=trial-support")
        assert backlog.status_code == 200
        backlog_payload = backlog.json()["data"]["trial_feedback_backlog"]
        assert backlog_payload["schema_version"] == "gw2radar.player_os_trial_feedback_backlog.v1"
        assert backlog_payload["backlog_items"][0]["blocker_id"] == "deep_link_not_opened"
        assert backlog_payload["unmapped_blockers"] == []

        queue = local_client.get("/api/v1/player-os/trial-feedback/refactor-queue?reviewer=trial-support")
        queue_md = local_client.get("/api/v1/player-os/trial-feedback/refactor-queue?reviewer=trial-support&format=markdown")
        queue_csv = local_client.get("/api/v1/player-os/trial-feedback/refactor-queue?reviewer=trial-support&format=csv")
        bundle = local_client.get("/api/v1/player-os/trial-feedback/action-bundle?reviewer=trial-support")
        assert queue.status_code == 200
        queue_payload = queue.json()["data"]["trial_refactor_queue"]
        assert queue_payload["schema_version"] == "gw2radar.player_os_trial_refactor_queue.v1"
        assert queue_payload["tasks"][0]["task_id"] == "trial-refactor-deep_link_not_opened"
        assert "src/gw2radar/ui/static/app.js" in queue_payload["tasks"][0]["target_files"]
        assert "python harness/run_stage_gate.py stage" in queue_payload["tasks"][0]["verification_commands"]
        assert queue_md.status_code == 200
        assert "Player OS Trial Targeted Refactor Queue" in queue_md.text
        assert "trial-refactor-deep_link_not_opened" in queue_md.text
        assert queue_csv.status_code == 200
        assert "task_id,priority,blocker_id" in queue_csv.text
        assert "trial-refactor-deep_link_not_opened" in queue_csv.text
        assert bundle.status_code == 200
        bundle_payload = bundle.json()["data"]["trial_feedback_action_bundle"]
        assert bundle_payload["schema_version"] == "gw2radar.player_os_trial_feedback_action_bundle.v1"
        assert bundle_payload["readiness_label"] == "targeted_refactor_ready"
        assert bundle_payload["refactor_queue"]["task_count"] == 1
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)


def _trial_feedback(ready: bool, missing_row: str | None = None) -> dict:
    rows = [
        {"id": "intent", "label": "Intent captured", "ready": True, "evidence": "legendary"},
        {"id": "plan", "label": "Plan generated", "ready": True, "evidence": "plan-sample"},
        {"id": "deep_link", "label": "Deep-link opened", "ready": True, "evidence": "legendary"},
        {"id": "report_preview", "label": "Report preview opened", "ready": True, "evidence": "report-sample"},
        {"id": "feedback_packet", "label": "Feedback metadata ready", "ready": True, "evidence": "metadata_only_ready"},
    ]
    for row in rows:
        if row["id"] == missing_row:
            row["ready"] = False
            row["evidence"] = "missing"
    ready_count = sum(1 for row in rows if row["ready"])
    return {
        "schema_version": "gw2radar.player_os_trial_feedback.v1",
        "checklist": {
            "schema_version": "gw2radar.player_os_trial_checklist.v1",
            "status": "ready" if ready else "in_progress",
            "ready_count": ready_count,
            "total_count": 5,
            "plan_id": "plan-sample",
            "report_id": "report-sample",
            "last_bridge": {"target_view": "legendary", "action_id": "action-1"},
            "rows": rows,
            "safety_boundary": "Metadata-only trial feedback; no raw API keys, private payloads, or automated actions.",
        },
        "player_os_context": {
            "plan_id": "plan-sample",
            "report_id": "report-sample",
            "last_bridge": {"target_view": "legendary", "action_id": "action-1"},
        },
        "safety_boundary": "Metadata-only trial feedback; no raw API keys, private payloads, or automated actions.",
    }
