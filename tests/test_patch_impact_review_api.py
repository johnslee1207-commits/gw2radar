from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_patch_impact_review_api_lists_and_reviews_existing_patch(monkeypatch) -> None:
    temp_dir = Path(".test_tmp") / f"patch-review-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        monkeypatch.setenv("GW2RADAR_PATCH_REVIEW_STORE", str(temp_dir / "reviews.jsonl"))
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        client = TestClient(app)

        listed = client.get("/api/v1/kb/patch-impact/drafts?year=2026&pending_only=true")
        patch_id = listed.json()["data"]["drafts"][0]["patch_id"]
        reviewed = client.post(
            "/api/v1/kb/patch-impact/reviews",
            json={
                "patch_id": patch_id,
                "affected_systems": ["build", "market", "game_update"],
                "build_impact": ["Review build recommendations affected by this patch."],
                "market_impact": ["Watch price movement before recommending purchases."],
                "reviewer": "api-test",
                "notes": "Reviewed source summary.",
            },
        )
        candidate = client.get(f"/api/v1/kb/patch-impact/{patch_id}/rule-candidates")
        blocked_persist = client.post(
            f"/api/v1/kb/patch-impact/{patch_id}/rule-candidates/persist",
            json={"confirmed": False},
        )
        persisted = client.post(
            f"/api/v1/kb/patch-impact/{patch_id}/rule-candidates/persist",
            json={"confirmed": True},
        )
        rule_id = persisted.json()["data"]["rules"][0]["rule_id"]
        blocked_enable = client.post(f"/api/v1/kb/rules/{rule_id}/enable", json={"confirmed_reviewed": False})
        enabled = client.post(f"/api/v1/kb/rules/{rule_id}/enable", json={"confirmed_reviewed": True})

        assert listed.status_code == 200
        assert listed.json()["data"]["count"] >= 1
        assert reviewed.status_code == 200
        assert reviewed.json()["data"]["review"]["review_status"] == "reviewed"
        assert candidate.status_code == 200
        assert [rule["enabled"] for rule in candidate.json()["data"]["rules"]] == [False, False]
        assert blocked_persist.status_code == 400
        assert persisted.status_code == 200
        assert persisted.json()["data"]["created_count"] == 2
        assert [rule["enabled"] for rule in persisted.json()["data"]["rules"]] == [False, False]
        assert blocked_enable.status_code == 400
        assert enabled.status_code == 200
        assert enabled.json()["data"]["rule"]["enabled"] is True
    finally:
        close_database()
