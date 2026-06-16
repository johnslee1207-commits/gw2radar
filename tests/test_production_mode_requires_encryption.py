import pytest

from gw2radar.config.settings import Settings
from gw2radar.security.encrypted_database_secret_store import EncryptedDatabaseSecretStore
from gw2radar.security.encrypted_local_secret_store import EncryptedLocalSecretStore
from gw2radar.security.in_memory_secret_store import InMemorySecretStore
from gw2radar.security.store_factory import build_secret_store


def test_test_mode_uses_in_memory_secret_store() -> None:
    store = build_secret_store(Settings(deployment_mode="test"))
    assert isinstance(store, InMemorySecretStore)


def test_local_only_requires_encrypted_store_session() -> None:
    with pytest.raises(ValueError):
        build_secret_store(Settings(deployment_mode="local_only"), session=None)


def test_hosted_saas_requires_encrypted_database_store_session() -> None:
    with pytest.raises(ValueError):
        build_secret_store(Settings(deployment_mode="hosted_saas"), session=None)


def test_store_factory_selects_encrypted_stores_when_session_is_present(mocker=None) -> None:
    class DummySession:
        pass

    assert isinstance(build_secret_store(Settings(deployment_mode="local_only"), DummySession()), EncryptedLocalSecretStore)
    assert isinstance(build_secret_store(Settings(deployment_mode="hosted_saas"), DummySession()), EncryptedDatabaseSecretStore)
