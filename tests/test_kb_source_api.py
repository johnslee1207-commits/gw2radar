from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_kb_source_api_create_list_and_get() -> None:
    temp_dir = Path(".test_tmp") / f"kb-source-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        client = TestClient(app)

        created = client.post(
            "/api/v1/kb/sources",
            json={
                "name": "Official GW2 API",
                "source_type": "official_api",
                "base_url": "https://api.guildwars2.com/",
                "allowed_use": "api_json",
                "crawl_policy": "api_only",
                "rate_limit_policy": "gateway_managed",
                "license_note": "Use through governed gateway.",
                "default_confidence": 0.95,
            },
        )
        source_id = created.json()["data"]["source"]["source_id"]
        listed = client.get("/api/v1/kb/sources", params={"source_type": "official_api"})
        loaded = client.get(f"/api/v1/kb/sources/{source_id}")

        assert created.status_code == 200
        assert listed.status_code == 200
        assert listed.json()["data"]["sources"][0]["source_id"] == source_id
        assert loaded.status_code == 200
        assert loaded.json()["data"]["source"]["allowed_use"] == "api_json"
    finally:
        close_database()
