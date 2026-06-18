import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.api.routes import account
from gw2radar.db.session import close_database, configure_database
from gw2radar.security.api_key_permissions import build_missing_key_permission_report, build_permission_report


def test_permission_report_marks_missing_permissions_without_key_leak() -> None:
    report = build_permission_report({"name": "Unit Test Key", "permissions": ["account", "wallet"]})

    assert report.key_configured is True
    assert report.token_name == "Unit Test Key"
    assert report.limited_mode is True
    assert "characters" in report.missing_required_permissions
    assert "inventories" in report.missing_required_permissions
    assert "progression" in report.missing_required_permissions
    assert "12345678-secret" not in report.model_dump_json()
    assert any(impact.feature_id == "market_context" and impact.status == "ready" for impact in report.feature_impacts)


def test_missing_key_permission_report_blocks_private_features() -> None:
    report = build_missing_key_permission_report()

    assert report.key_configured is False
    assert report.limited_mode is True
    assert report.granted_permissions == []
    assert all(impact.status in {"blocked", "ready"} for impact in report.feature_impacts)
    assert any(impact.feature_id == "build_fit" and impact.status == "blocked" for impact in report.feature_impacts)


def test_api_key_permission_endpoint_uses_stored_key_without_returning_it() -> None:
    temp_dir = Path(".test_tmp") / f"api-key-permissions-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    raw_key = "12345678-abcdef-secret-key"

    class FakeGateway:
        def _fetch_tokeninfo(self, api_key: str, *, request_id: str) -> dict:
            assert api_key == raw_key
            assert request_id == "account:permissions:tokeninfo"
            return {
                "name": "Local Test Key",
                "permissions": ["account", "characters", "inventories", "progression", "wallet", "builds"],
            }

    original_factory = account.permission_gateway_factory
    try:
        configure_database(f"sqlite:///{temp_dir / 'account.db'}")
        account.permission_gateway_factory = FakeGateway
        client = TestClient(app)

        assert client.put("/account/api-key", json={"api_key": raw_key}).status_code == 200
        response = client.get("/account/api-key/permissions")
        payload = response.json()

        assert response.status_code == 200
        assert payload["schema_version"] == "gw2radar.api_key_permissions.v1"
        assert payload["key_configured"] is True
        assert payload["limited_mode"] is False
        assert payload["missing_required_permissions"] == []
        assert payload["token_name"] == "Local Test Key"
        assert raw_key not in str(payload)
    finally:
        account.permission_gateway_factory = original_factory
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_api_key_permission_endpoint_reports_limited_mode_without_key() -> None:
    temp_dir = Path(".test_tmp") / f"api-key-permissions-empty-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'account.db'}")
        client = TestClient(app)

        response = client.get("/account/api-key/permissions")
        payload = response.json()

        assert response.status_code == 200
        assert payload["key_configured"] is False
        assert payload["limited_mode"] is True
        assert payload["granted_permissions"] == []
        assert any(impact["status"] == "blocked" for impact in payload["feature_impacts"])
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)
