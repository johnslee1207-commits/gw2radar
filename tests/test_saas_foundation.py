from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.config.settings import Settings
from gw2radar.saas.production_foundation import build_production_saas_foundation


def test_local_first_saas_foundation_keeps_local_mode_supported() -> None:
    foundation = build_production_saas_foundation(Settings(deployment_mode="local_only"))

    assert foundation.schema_version == "gw2radar.production_saas_foundation.v1"
    assert foundation.deployment_mode == "local_only"
    assert foundation.local_first_supported is True
    assert foundation.ready_for_hosted_saas is False
    assert foundation.missing_gates == []
    assert foundation.workspace.workspace_id == "local-workspace"
    assert foundation.auth_session.auth_required is False
    assert foundation.adapters.billing_guard["real_payment_enabled"] is False
    assert "real payment provider" in foundation.deferred_capabilities
    assert "team workspace credential sharing" in foundation.deferred_capabilities


def test_hosted_saas_foundation_requires_production_adapters_and_mock_billing_guard() -> None:
    foundation = build_production_saas_foundation(
        Settings(
            deployment_mode="hosted_saas",
            database_url="sqlite:///./gw2radar.db",
            redis_url=None,
            object_storage_backend="local_filesystem",
            billing_provider="stripe",
        )
    )

    assert foundation.deployment_mode == "hosted_saas"
    assert foundation.ready_for_hosted_saas is False
    assert foundation.auth_session.auth_required is True
    assert foundation.workspace.persistence_scope == "postgres_planned"
    assert any("PostgreSQL" in gate for gate in foundation.missing_gates)
    assert any("Redis" in gate for gate in foundation.missing_gates)
    assert any("Object storage" in gate for gate in foundation.missing_gates)
    assert foundation.blockers == ["Real billing provider is configured but Phase E allows mock billing guard only."]
    assert foundation.adapters.billing_guard["real_payment_enabled"] is False


def test_saas_foundation_api_is_metadata_only_and_exposes_boundaries() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/saas/foundation")

    assert response.status_code == 200
    foundation = response.json()["data"]["foundation"]
    assert foundation["schema_version"] == "gw2radar.production_saas_foundation.v1"
    assert foundation["local_first_supported"] is True
    assert "full multi-tenant SaaS launch" in foundation["deferred_capabilities"]
    combined = str(foundation).lower()
    assert "secret-key" not in combined
    assert "raw api key" not in combined
    assert "real_payment_enabled': true" not in combined
