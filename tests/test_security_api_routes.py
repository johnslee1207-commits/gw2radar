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


def test_credential_center_session_only_mode_does_not_persist_key() -> None:
    temp_dir = Path(".test_tmp") / f"credential-session-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    raw_key = " 12345678-abcdef-secret-key "
    try:
        configure_database(f"sqlite:///{temp_dir / 'security.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        preview = client.post(
            "/api/v1/security/api-key",
            json={"api_key": raw_key, "mode": "session_only"},
        )
        status = client.get("/api/v1/security/api-key/status")
        center = client.get("/api/v1/security/credential-center")

        assert preview.status_code == 200
        assert preview.json()["data"]["credential_mode"] == "session_only"
        assert preview.json()["data"]["persisted"] is False
        assert preview.json()["data"]["has_api_key"] is True
        assert raw_key.strip() not in str(preview.json())
        assert status.json()["data"]["has_api_key"] is False
        assert center.json()["data"]["default_mode"] == "session_only"
        assert any(mode["mode"] == "encrypted_persistent" for mode in center.json()["data"]["available_modes"])
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_credential_center_rotate_revoke_and_audit_are_metadata_only() -> None:
    temp_dir = Path(".test_tmp") / f"credential-rotate-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    old_key = "12345678-abcdef-secret-key"
    new_key = "87654321-fedcba-secret-key"
    try:
        configure_database(f"sqlite:///{temp_dir / 'security.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        saved = client.post("/api/v1/security/api-key", json={"api_key": old_key})
        rotated = client.post("/api/v1/security/api-key/rotate", json={"api_key": new_key})
        audit = client.get("/api/v1/security/credential-center/audit")
        deleted = client.delete("/api/v1/security/api-key")

        combined = str(saved.json()) + str(rotated.json()) + str(audit.json()) + str(deleted.json())
        assert saved.json()["data"]["credential_mode"] == "encrypted_persistent"
        assert rotated.json()["data"]["audit_event"]["event_type"] == "credential_rotated"
        assert audit.json()["data"]["schema_version"] == "gw2radar.credential_audit_summary.v1"
        assert audit.json()["data"]["events"][0]["raw_key_returned"] is False
        assert deleted.json()["data"]["audit_event"]["event_type"] == "credential_revoked"
        assert old_key not in combined
        assert new_key not in combined
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_permission_explanation_states_what_is_not_accessed() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/security/credential-center/permission-explanation")

    payload = response.json()["data"]
    text = str(payload).lower()
    assert response.status_code == 200
    assert payload["schema_version"] == "gw2radar.credential_permission_explanation.v1"
    assert "password" in text
    assert "email" in text
    assert "automatic gear changes" in text
    assert "placing orders" in text
    assert "never trades" in payload["manual_review_boundary"].lower()
