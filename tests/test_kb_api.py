from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_kb_api_article_list_search_review_and_deprecate() -> None:
    temp_dir = Path(".test_tmp") / f"kb-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        client = TestClient(app)

        created = client.post(
            "/api/v1/kb/articles",
            json={
                "title": "Returner mobility note",
                "domain": "returner",
                "content_type": "summary",
                "summary": "Returning players should recover mobility before advanced goals.",
                "body_markdown": "Mount and map movement explanations should stay source-linked and concise.",
                "linked_entities": ["gw2:mount:raptor"],
                "linked_actions": ["complete_achievement"],
                "confidence": 0.7,
            },
        )
        kb_id = created.json()["data"]["article"]["kb_id"]
        listed = client.get("/api/v1/kb/articles", params={"domain": "returner"})
        loaded = client.get(f"/api/v1/kb/articles/{kb_id}")
        searched = client.get("/api/v1/kb/search", params={"q": "mobility", "domain": "returner"})
        reviewed = client.post(f"/api/v1/kb/articles/{kb_id}/review")
        deprecated = client.post(f"/api/v1/kb/articles/{kb_id}/deprecate")

        assert created.status_code == 200
        assert listed.status_code == 200
        assert listed.json()["data"]["articles"][0]["kb_id"] == kb_id
        assert loaded.status_code == 200
        assert searched.status_code == 200
        assert searched.json()["data"]["articles"][0]["kb_id"] == kb_id
        assert reviewed.json()["data"]["article"]["review_status"] == "reviewed"
        assert deprecated.json()["data"]["article"]["review_status"] == "deprecated"
    finally:
        close_database()


def test_kb_api_rejects_unsafe_article_content() -> None:
    temp_dir = Path(".test_tmp") / f"kb-api-unsafe-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        client = TestClient(app)

        response = client.post(
            "/api/v1/kb/articles",
            json={
                "title": "Unsafe note",
                "domain": "official",
                "content_type": "summary",
                "summary": "This note contains private inventory details.",
            },
        )

        assert response.status_code == 422
    finally:
        close_database()
