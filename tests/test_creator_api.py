from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_creator_api_import_topics_opportunities_and_report() -> None:
    temp_dir = Path(".test_tmp") / f"creator-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'creator.db'}")
        init_db()
        client = TestClient(app)

        first = client.post(
            "/api/v1/creator/signals/import",
            json={
                "source_type": "public_forum",
                "source_url": "https://example.com/forum/returner",
                "title": "How do I start gearing after returning?",
                "summary": "A public forum question asks for a compact returner gearing plan.",
                "topic": "returner gearing",
                "audience_segment": "returning_player",
                "signal_kind": "question",
                "confidence": 0.8,
            },
        )
        second = client.post(
            "/api/v1/creator/signals/import",
            json={
                "source_type": "reddit",
                "source_url": "https://example.com/r/guildwars2/gearing",
                "title": "What should I craft first?",
                "summary": "A second attributed question asks for a cheap upgrade order.",
                "topic": "returner gearing",
                "audience_segment": "returning_player",
                "signal_kind": "question",
                "confidence": 0.7,
            },
        )
        topics = client.get("/api/v1/creator/topics")
        opportunities = client.get("/api/v1/creator/opportunities")
        report = client.post("/api/v1/creator/report")

        assert first.status_code == 200
        assert second.status_code == 200
        assert topics.status_code == 200
        assert topics.json()["data"]["topics"][0]["signal_count"] == 2
        assert opportunities.status_code == 200
        assert opportunities.json()["data"]["opportunities"][0]["topic"] == "returner gearing"
        assert report.status_code == 200
        assert "Creator Intelligence Report" in report.text
    finally:
        close_database()
