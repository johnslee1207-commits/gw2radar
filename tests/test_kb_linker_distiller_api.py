from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_kb_api_validate_links_and_distill_rule() -> None:
    temp_dir = Path(".test_tmp") / f"kb-link-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        client.post("/mock/load")

        created = client.post(
            "/api/v1/kb/articles",
            json={
                "title": "Legendary hold rule",
                "domain": "legendary",
                "content_type": "rule",
                "summary": "Hold active legendary materials before surplus decisions.",
                "body_markdown": "This report rule protects active goals first.",
                "linked_entities": ["gw2:item:mystic_clover"],
                "linked_actions": ["hold"],
                "confidence": 0.85,
                "review_status": "reviewed",
            },
        )
        kb_id = created.json()["data"]["article"]["kb_id"]
        validated = client.post(f"/api/v1/kb/articles/{kb_id}/validate-links")
        distilled = client.post(f"/api/v1/kb/articles/{kb_id}/distill-rule")

        assert created.status_code == 200
        assert validated.status_code == 200
        assert validated.json()["data"]["validation"]["missing_entities"] == []
        assert validated.json()["data"]["validation"]["invalid_actions"] == []
        assert distilled.status_code == 200
        assert distilled.json()["data"]["rule"]["action_type"] == "hold"
    finally:
        close_database()
        state.reset_cached_graph()
