import os
from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    database_url: str = "sqlite:///./gw2radar.db"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("GW2RADAR_DATABASE_URL", "sqlite:///./gw2radar.db"),
    )
