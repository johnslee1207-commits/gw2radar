import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    database_url: str = "sqlite:///./gw2radar.db"
    gw2_api_base_url: str = "https://api.guildwars2.com"
    gw2_api_key: str | None = None
    api_key_encryption_secret: str = "gw2radar-local-dev-secret"
    deployment_mode: str = "local_only"
    account_snapshot_retention_days: int = 30
    delete_exports_on_user_delete: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("GW2RADAR_DATABASE_URL", "sqlite:///./gw2radar.db"),
        gw2_api_base_url=os.getenv("GW2RADAR_API_BASE_URL", "https://api.guildwars2.com"),
        gw2_api_key=os.getenv("GW2RADAR_API_KEY"),
        api_key_encryption_secret=os.getenv(
            "GW2RADAR_API_KEY_ENCRYPTION_SECRET", "gw2radar-local-dev-secret"
        ),
        deployment_mode=os.getenv("GW2RADAR_DEPLOYMENT_MODE", "local_only"),
        account_snapshot_retention_days=int(os.getenv("GW2RADAR_ACCOUNT_SNAPSHOT_RETENTION_DAYS", "30")),
        delete_exports_on_user_delete=os.getenv("GW2RADAR_DELETE_EXPORTS_ON_USER_DELETE", "true").lower()
        == "true",
    )
