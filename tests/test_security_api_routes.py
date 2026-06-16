import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.db.session import close_database, configure_database


def test_security_api_key_save_status_delete_uses_encrypted_store() -> None:
    temp_dir = Path(".test_tmp") / f"security-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    raw_key = "12345678-abcdef-secret-key"
    try:
        configure_database(f"sqlite:///{temp_dir / 'security.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        saved = client.post("/api/v1/security/api-key", json={"api_key": raw_key})
        status = client.get("/api/v1/security/api-key/status")
        deleted = client.delete("/api/v1/security/api-key")
        final_status = client.get("/api/v1/security/api-key/status")

        assert saved.status_code == 200
        assert saved.json()["ok"] is True
        assert saved.json()["data"]["encrypted"] is True
        assert saved.json()["data"]["storage_backend"] == "encrypted_local"
        assert raw_key not in str(saved.json())
        assert status.json()["data"]["has_api_key"] is True
        assert deleted.json()["data"]["deleted"] is True
        assert final_status.json()["data"]["has_api_key"] is False
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
