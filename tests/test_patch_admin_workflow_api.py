from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_patch_admin_workflow_reviews_persists_enables_and_returns_dashboard_exports(monkeypatch) -> None:
    temp_dir = Path(".test_tmp") / f"patch-admin-workflow-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        monkeypatch.setenv("GW2RADAR_PATCH_REVIEW_STORE", str(temp_dir / "reviews.jsonl"))
        monkeypatch.setenv("GW2RADAR_PATCH_RULE_AUDIT_STORE", str(temp_dir / "audit.jsonl"))
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        client = TestClient(app)

        listed = client.get("/api/v1/kb/patch-impact/drafts?year=2026&pending_only=true")
        patch_id = listed.json()["data"]["drafts"][0]["patch_id"]
        reviewed_and_persisted = client.post(
            "/api/v1/kb/patch-impact/admin/workflow",
            json={
                "year": 2026,
                "patch_id": patch_id,
                "review": {
                    "patch_id": patch_id,
                    "affected_systems": ["build", "market", "game_update"],
                    "build_impact": ["Review build recommendations affected by this patch."],
                    "market_impact": ["Watch price movement before recommending purchases."],
                    "reviewer": "workflow-reviewer",
                },
                "persist_confirmed": True,
                "include_markdown_export": True,
                "include_csv_export": True,
            },
        )
        rules = reviewed_and_persisted.json()["data"]["actions"]["persist"]["rules"]
        enabled = client.post(
            "/api/v1/kb/patch-impact/admin/workflow",
            json={
                "year": 2026,
                "patch_id": patch_id,
                "enable_rule_ids": [rules[0]["rule_id"]],
                "enable_confirmed": True,
                "reviewer": "workflow-enabler",
            },
        )

        assert reviewed_and_persisted.status_code == 200
        data = reviewed_and_persisted.json()["data"]
        assert data["actions"]["review"]["reviewer"] == "workflow-reviewer"
        assert data["actions"]["persist"]["created_count"] == 2
        assert data["dashboard"]["lifecycle_counts"]["persisted"] >= 1
        assert "# Patch Review Dashboard" in data["exports"]["markdown"]
        assert "patch_id,date,year,lifecycle_status" in data["exports"]["csv"]
        assert [event["action"] for event in data["audit"]["events"]] == ["review", "persist", "persist"]

        assert enabled.status_code == 200
        enabled_data = enabled.json()["data"]
        item = next(item for item in enabled_data["dashboard"]["items"] if item["patch_id"] == patch_id)
        assert item["lifecycle_status"] == "enabled"
        assert item["operational_lifecycle"]["schema_version"] == "gw2radar.operational_lifecycle_summary.v1"
        assert item["operational_lifecycle"]["ready"] is True
        assert item["operational_lifecycle"]["current_stage"] == "enabled"
        assert item["enabled_rule_count"] == 1
        assert enabled_data["audit"]["events"][-1]["action"] == "enable"
        assert enabled_data["audit"]["events"][-1]["reviewer"] == "workflow-enabler"
    finally:
        close_database()


def test_patch_admin_workflow_keeps_confirmation_gates(monkeypatch) -> None:
    temp_dir = Path(".test_tmp") / f"patch-admin-gate-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        monkeypatch.setenv("GW2RADAR_PATCH_REVIEW_STORE", str(temp_dir / "reviews.jsonl"))
        monkeypatch.setenv("GW2RADAR_PATCH_RULE_AUDIT_STORE", str(temp_dir / "audit.jsonl"))
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        client = TestClient(app)

        blocked_persist = client.post(
            "/api/v1/kb/patch-impact/admin/workflow",
            json={"persist_confirmed": True},
        )
        blocked_enable = client.post(
            "/api/v1/kb/patch-impact/admin/workflow",
            json={"enable_rule_ids": ["kb_rule_missing"], "enable_confirmed": False},
        )

        assert blocked_persist.status_code == 400
        assert blocked_enable.status_code == 400
    finally:
        close_database()
