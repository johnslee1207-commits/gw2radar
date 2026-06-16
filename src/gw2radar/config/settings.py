import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    database_url: str = "sqlite:///./gw2radar.db"
    gw2_api_base_url: str = "https://api.guildwars2.com"
    gw2_api_key: str | None = None
    api_key_encryption_secret: str = "gw2radar-local-dev-secret"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("GW2RADAR_DATABASE_URL", "sqlite:///./gw2radar.db"),
        gw2_api_base_url=os.getenv("GW2RADAR_API_BASE_URL", "https://api.guildwars2.com"),
        gw2_api_key=os.getenv("GW2RADAR_API_KEY"),
        api_key_encryption_secret=os.getenv(
            "GW2RADAR_API_KEY_ENCRYPTION_SECRET", "gw2radar-local-dev-secret"
        ),
    )
