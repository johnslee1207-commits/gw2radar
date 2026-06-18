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


def test_support_review_playbook_maps_blockers_to_remediation_steps() -> None:
    temp_dir = Path(".test_tmp") / f"support-review-playbook-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'support-review-playbook.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        client.post("/account/debug-bundle/review/audit", json={"bundle": _missing_key_bundle(), "reviewer": "playbook"})
        client.post("/account/debug-bundle/review/audit", json={"bundle": _missing_permission_bundle(), "reviewer": "playbook"})

        playbook = client.get("/account/debug-bundle/review/audit/playbook?reviewer=playbook&limit=10").json()
        rendered = str(playbook)

        assert playbook["schema_version"] == "gw2radar.account_debug_bundle_review_playbook.v1"
        assert playbook["total_records"] == 2
        assert len(playbook["plays"]) == 2
        assert {play["blocker_id"] for play in playbook["plays"]} == {"needs_key", "needs_permissions"}
        assert all(play["support_steps"] for play in playbook["plays"])
        assert all("Do not send" in play["player_reply_template"] for play in playbook["plays"])
        assert any("Paste key" in " ".join(play["support_steps"]) or "paste" in play["player_reply_template"].lower() for play in playbook["plays"])
        assert "privacy-safe audit metadata" in playbook["boundary"]
        assert "Diagnostic Berserker Chest" not in rendered
        assert "12345678-1234-1234-1234-123456789abc" not in rendered
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_support_review_backlog_prioritizes_product_fixes_from_playbook() -> None:
    temp_dir = Path(".test_tmp") / f"support-review-backlog-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'support-review-backlog.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        client.post("/account/debug-bundle/review/audit", json={"bundle": _missing_key_bundle(), "reviewer": "backlog"})
        client.post("/account/debug-bundle/review/audit", json={"bundle": _missing_key_bundle(), "reviewer": "backlog"})
        client.post("/account/debug-bundle/review/audit", json={"bundle": _missing_permission_bundle(), "reviewer": "backlog"})

        backlog = client.get("/account/debug-bundle/review/audit/backlog?reviewer=backlog&limit=10").json()
        rendered = str(backlog)

        assert backlog["schema_version"] == "gw2radar.account_debug_bundle_review_backlog.v1"
        assert backlog["total_records"] == 3
        assert len(backlog["backlog_items"]) == 2
        first = backlog["backlog_items"][0]
        assert first["blocker_id"] == "needs_key"
        assert first["priority"] == "P0"
        assert first["affected_cases"] == 2
        assert "key input" in first["product_fix_suggestion"]
        assert first["acceptance_criteria"]
        assert "privacy-safe support metadata" in backlog["boundary"]
        assert "Diagnostic Berserker Chest" not in rendered
        assert "12345678-1234-1234-1234-123456789abc" not in rendered
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_support_review_backlog_exports_markdown_and_csv() -> None:
    temp_dir = Path(".test_tmp") / f"support-review-backlog-export-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'support-review-backlog-export.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        client.post("/account/debug-bundle/review/audit", json={"bundle": _missing_key_bundle(), "reviewer": "export"})
        markdown = client.get("/account/debug-bundle/review/audit/backlog?reviewer=export&format=markdown")
        csv_response = client.get("/account/debug-bundle/review/audit/backlog?reviewer=export&format=csv")

        assert markdown.status_code == 200
        assert "text/markdown" in markdown.headers["content-type"]
        assert "# Support Review Product Backlog" in markdown.text
        assert "## P0 - API key is not connected" in markdown.text
        assert "Acceptance criteria" in markdown.text
        assert "Diagnostic Berserker Chest" not in markdown.text

        assert csv_response.status_code == 200
        assert "text/csv" in csv_response.headers["content-type"]
        assert "backlog_id,priority,blocker_id,title,affected_cases" in csv_response.text
        assert "support-backlog-needs_key" in csv_response.text
        assert "Diagnostic Berserker Chest" not in csv_response.text
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_support_review_backlog_promotes_to_safe_product_draft() -> None:
    temp_dir = Path(".test_tmp") / f"support-review-backlog-promotion-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'support-review-backlog-promotion.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        client.post("/account/debug-bundle/review/audit", json={"bundle": _missing_key_bundle(), "reviewer": "promoter"})
        client.post("/account/debug-bundle/review/audit", json={"bundle": _missing_key_bundle(), "reviewer": "promoter"})

        response = client.post(
            "/account/debug-bundle/review/audit/backlog/promotions",
            json={
                "backlog_id": "support-backlog-needs_key",
                "reviewer": "product lead",
                "audit_reviewer": "promoter",
                "artifact_type": "roadmap_issue_draft",
            },
        )
        payload = response.json()
        rendered = str(payload)

        assert response.status_code == 200
        assert payload["schema_version"] == "gw2radar.support_backlog_promotion_result.v1"
        assert payload["status"] == "created"
        promotion = payload["promotion"]
        assert promotion["backlog_id"] == "support-backlog-needs_key"
        assert promotion["blocker_id"] == "needs_key"
        assert promotion["status"] == "draft"
        assert promotion["reviewer"] == "product lead"
        assert "Support Signal" in promotion["body_markdown"]
        assert "Do not request raw GW2 API keys" in promotion["body_markdown"]
        assert promotion["properties"]["affected_cases"] == 2
        assert promotion["properties"]["stores_raw_bundle"] is False
        assert promotion["properties"]["stores_raw_api_key"] is False
        assert promotion["properties"]["stores_private_account_payload"] is False
        assert "Diagnostic Berserker Chest" not in rendered
        assert "12345678-1234-1234-1234-123456789abc" not in rendered

        listing = client.get("/account/debug-bundle/review/audit/backlog/promotions?reviewer=product%20lead").json()
        assert listing["schema_version"] == "gw2radar.support_backlog_promotion_list.v1"
        assert len(listing["promotions"]) == 1
        assert listing["promotions"][0]["promotion_id"] == promotion["promotion_id"]

        markdown = client.get("/account/debug-bundle/review/audit/backlog/promotions?reviewer=product%20lead&format=markdown")
        csv_response = client.get("/account/debug-bundle/review/audit/backlog/promotions?reviewer=product%20lead&format=csv")

        assert markdown.status_code == 200
        assert "text/markdown" in markdown.headers["content-type"]
        assert "# Support Backlog Promotion Drafts" in markdown.text
        assert promotion["promotion_id"] in markdown.text
        assert "Diagnostic Berserker Chest" not in markdown.text

        assert csv_response.status_code == 200
        assert "text/csv" in csv_response.headers["content-type"]
        assert "promotion_id,backlog_id,blocker_id,priority,title" in csv_response.text
        assert promotion["promotion_id"] in csv_response.text
        assert "Diagnostic Berserker Chest" not in csv_response.text
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_support_review_backlog_promotion_reports_missing_backlog_id() -> None:
    temp_dir = Path(".test_tmp") / f"support-review-backlog-promotion-missing-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'support-review-backlog-promotion-missing.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        client.post("/account/debug-bundle/review/audit", json={"bundle": _missing_key_bundle(), "reviewer": "promoter"})
        response = client.post(
            "/account/debug-bundle/review/audit/backlog/promotions",
            json={"backlog_id": "support-backlog-unknown", "reviewer": "product lead", "audit_reviewer": "promoter"},
        )
        payload = response.json()

        assert response.status_code == 200
        assert payload["status"] == "not_found"
        assert payload["promotion"] is None
        assert payload["available_backlog_ids"] == ["support-backlog-needs_key"]
        assert "raw API key" in payload["boundary"]
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_support_review_backlog_promotion_status_events_are_auditable() -> None:
    temp_dir = Path(".test_tmp") / f"support-review-backlog-promotion-events-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'support-review-backlog-promotion-events.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        client.post("/account/debug-bundle/review/audit", json={"bundle": _missing_key_bundle(), "reviewer": "events"})
        created = client.post(
            "/account/debug-bundle/review/audit/backlog/promotions",
            json={"backlog_id": "support-backlog-needs_key", "reviewer": "product lead", "audit_reviewer": "events"},
        ).json()
        promotion_id = created["promotion"]["promotion_id"]

        accepted = client.post(
            f"/account/debug-bundle/review/audit/backlog/promotions/{promotion_id}/status",
            json={"status": "accepted", "reviewer": "product lead", "note": "Accepted for next sprint."},
        )
        linked = client.post(
            f"/account/debug-bundle/review/audit/backlog/promotions/{promotion_id}/status",
            json={
                "status": "linked",
                "reviewer": "product lead",
                "note": "Linked to local roadmap item.",
                "external_ref": "ROADMAP-12",
            },
        )
        events = client.get(f"/account/debug-bundle/review/audit/backlog/promotions/events?promotion_id={promotion_id}").json()
        markdown = client.get(
            f"/account/debug-bundle/review/audit/backlog/promotions/events?promotion_id={promotion_id}&format=markdown"
        )
        csv_response = client.get(
            f"/account/debug-bundle/review/audit/backlog/promotions/events?promotion_id={promotion_id}&format=csv"
        )
        invalid = client.post(
            f"/account/debug-bundle/review/audit/backlog/promotions/{promotion_id}/status",
            json={"status": "shipping-now", "reviewer": "product lead"},
        ).json()

        assert accepted.status_code == 200
        assert accepted.json()["status"] == "updated"
        assert accepted.json()["promotion"]["status"] == "accepted"
        assert linked.status_code == 200
        assert linked.json()["promotion"]["status"] == "linked"
        assert linked.json()["promotion"]["properties"]["external_ref"] == "ROADMAP-12"

        assert events["schema_version"] == "gw2radar.support_backlog_promotion_events.v1"
        assert len(events["events"]) == 3
        assert events["events"][0]["new_status"] == "linked"
        assert events["events"][1]["previous_status"] == "draft"
        assert events["events"][2]["action"] == "created"
        assert "raw support bundles" in events["boundary"]

        assert "text/markdown" in markdown.headers["content-type"]
        assert "# Support Backlog Promotion Events" in markdown.text
        assert "Accepted for next sprint" in markdown.text
        assert "Diagnostic Berserker Chest" not in markdown.text

        assert "text/csv" in csv_response.headers["content-type"]
        assert "event_id,promotion_id,action,previous_status,new_status" in csv_response.text
        assert promotion_id in csv_response.text
        assert "Diagnostic Berserker Chest" not in csv_response.text

        assert invalid["status"] == "invalid_status"
        assert invalid["allowed_statuses"] == ["draft", "accepted", "linked", "closed"]
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_support_promotion_readiness_rollup_summarizes_product_handoff_state() -> None:
    temp_dir = Path(".test_tmp") / f"support-promotion-readiness-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'support-promotion-readiness.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        client.post("/account/debug-bundle/review/audit", json={"bundle": _missing_key_bundle(), "reviewer": "readiness"})
        client.post("/account/debug-bundle/review/audit", json={"bundle": _missing_permission_bundle(), "reviewer": "readiness"})

        blocked = client.get("/account/debug-bundle/review/audit/backlog/promotions/readiness?audit_reviewer=readiness").json()

        assert blocked["schema_version"] == "gw2radar.support_promotion_readiness_rollup.v1"
        assert blocked["ready"] is False
        assert blocked["maturity_label"] == "blocked"
        assert blocked["audit_total"] == 2
        assert blocked["backlog_total"] == 2
        assert blocked["promotion_total"] == 0
        assert blocked["unpromoted_backlog_ids"] == ["support-backlog-needs_key", "support-backlog-needs_permissions"]
        assert any("none have been promoted" in blocker for blocker in blocked["blockers"])

        created = client.post(
            "/account/debug-bundle/review/audit/backlog/promotions",
            json={"backlog_id": "support-backlog-needs_key", "reviewer": "product", "audit_reviewer": "readiness"},
        ).json()
        promotion_id = created["promotion"]["promotion_id"]
        client.post(
            f"/account/debug-bundle/review/audit/backlog/promotions/{promotion_id}/status",
            json={"status": "linked", "reviewer": "product", "note": "Linked to readiness gate.", "external_ref": "ROADMAP-22"},
        )

        rollup_response = client.get(
            "/account/debug-bundle/review/audit/backlog/promotions/readiness?audit_reviewer=readiness&promotion_reviewer=product"
        )
        rollup = rollup_response.json()
        markdown = client.get(
            "/account/debug-bundle/review/audit/backlog/promotions/readiness?audit_reviewer=readiness&promotion_reviewer=product&format=markdown"
        )
        csv_response = client.get(
            "/account/debug-bundle/review/audit/backlog/promotions/readiness?audit_reviewer=readiness&promotion_reviewer=product&format=csv"
        )

        assert rollup_response.status_code == 200
        assert rollup["ready"] is True
        assert rollup["maturity_label"] == "operable_with_warnings"
        assert rollup["readiness_score"] >= 80
        assert rollup["promotion_total"] == 1
        assert rollup["event_total"] == 2
        assert rollup["unpromoted_backlog_ids"] == ["support-backlog-needs_permissions"]
        assert any(item["key"] == "linked" and item["count"] == 1 for item in rollup["status_counts"])
        assert any("not been promoted" in warning for warning in rollup["warnings"])
        assert any("Promote or explicitly defer" in step for step in rollup["next_steps"])
        assert "/account/debug-bundle/review/audit/backlog/promotions/events" in rollup["evidence_chain"]
        assert "Diagnostic Berserker Chest" not in str(rollup)

        assert "text/markdown" in markdown.headers["content-type"]
        assert "# Support Promotion Readiness Rollup" in markdown.text
        assert "operable_with_warnings" in markdown.text
        assert "Diagnostic Berserker Chest" not in markdown.text

        assert "text/csv" in csv_response.headers["content-type"]
        assert "ready,maturity_label,readiness_score,audit_total" in csv_response.text
        assert "support-backlog-needs_permissions" in csv_response.text
        assert "Diagnostic Berserker Chest" not in csv_response.text
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
