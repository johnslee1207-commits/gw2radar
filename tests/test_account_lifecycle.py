import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.db.session import close_database, configure_database
from gw2radar.security.api_key_store import api_key_store


def test_api_key_lifecycle_masks_and_deletes_key() -> None:
    client = TestClient(app)
    raw_key = "12345678-abcdef-secret-key"

    stored = client.put("/account/api-key", json={"api_key": raw_key})
    status = client.get("/account/api-key/status")
    deleted = client.delete("/account/api-key")

    assert stored.status_code == 200
    assert stored.json()["is_configured"] is True
    assert stored.json()["masked_key"] == "1234...-key"
    assert raw_key not in str(stored.json())
    assert status.json()["masked_key"] == "1234...-key"
    assert deleted.json()["is_configured"] is False
    assert deleted.json()["masked_key"] is None


def test_delete_account_snapshot_removes_private_and_personal_layers() -> None:
    temp_dir = Path(".test_tmp") / f"account-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'account.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        assert client.post("/mock/load").status_code == 200
        assert client.post("/goals/gw2:goal:aurora/actions/generate").status_code == 200

        deleted = client.delete("/account/snapshot")
        assert deleted.status_code == 200
        assert deleted.json()["status"] == "deleted"
        assert deleted.json()["deleted"]["player_state"] > 0
        assert deleted.json()["deleted"]["actions"] > 0

        state.reset_cached_graph()
        goals = client.get("/goals")
        gap = client.get("/goals/gw2:goal:aurora/gap")

        assert goals.status_code == 200
        assert goals.json()[0]["id"] == "gw2:goal:aurora"
        assert gap.status_code == 200
        assert all(item["owned_quantity"] == 0 for item in gap.json()["missing_requirements"])
    finally:
        api_key_store.delete()
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
