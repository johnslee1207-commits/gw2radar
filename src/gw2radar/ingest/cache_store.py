from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


ENDPOINT_TTL_SECONDS: dict[str, int] = {
    "items": 72 * 60 * 60,
    "recipes": 72 * 60 * 60,
    "achievements": 72 * 60 * 60,
    "currencies": 72 * 60 * 60,
    "account": 30 * 60,
    "characters": 30 * 60,
    "wallet": 30 * 60,
    "materials": 30 * 60,
    "bank": 30 * 60,
    "account_achievements": 60 * 60,
    "commerce_prices_goal_items": 30 * 60,
    "commerce_listings": 60 * 60,
}


@dataclass
class CacheEntry:
    payload: Any
    expires_at: datetime


class InMemoryCacheStore:
    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}

    def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= datetime.now(timezone.utc):
            self._entries.pop(key, None)
            return None
        return entry.payload

    def set(self, key: str, payload: Any, ttl_seconds: int) -> None:
        self._entries[key] = CacheEntry(
            payload=payload,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
        )
