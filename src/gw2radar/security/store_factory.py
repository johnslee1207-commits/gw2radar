from sqlalchemy.orm import Session

from gw2radar.config.settings import Settings
from gw2radar.security.deployment_mode import DeploymentMode
from gw2radar.security.encrypted_database_secret_store import EncryptedDatabaseSecretStore
from gw2radar.security.encrypted_local_secret_store import EncryptedLocalSecretStore
from gw2radar.security.in_memory_secret_store import InMemorySecretStore


def build_secret_store(settings: Settings, session: Session | None = None):
    mode = DeploymentMode(settings.deployment_mode)
    if mode is DeploymentMode.TEST:
        return InMemorySecretStore()
    if mode is DeploymentMode.LOCAL_ONLY:
        if session is None:
            raise ValueError("Encrypted local secret store requires a database session.")
        return EncryptedLocalSecretStore(session)
    if mode is DeploymentMode.HOSTED_SAAS:
        if session is None:
            raise ValueError("Encrypted database secret store requires a database session.")
        return EncryptedDatabaseSecretStore(session)
    raise ValueError(f"Unsupported deployment mode: {settings.deployment_mode}")
