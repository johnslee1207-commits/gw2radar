from dataclasses import dataclass

from gw2radar.ingest.security import mask_api_key


@dataclass(frozen=True)
class ApiKeyStatus:
    is_configured: bool
    masked_key: str | None = None
    storage: str = "memory_only"


class InMemoryApiKeyStore:
    def __init__(self) -> None:
        self._api_key: str | None = None

    def set(self, api_key: str) -> ApiKeyStatus:
        if not api_key or not api_key.strip():
            raise ValueError("API key must not be empty.")
        self._api_key = api_key.strip()
        return self.status()

    def get(self) -> str | None:
        return self._api_key

    def delete(self) -> ApiKeyStatus:
        self._api_key = None
        return self.status()

    def status(self) -> ApiKeyStatus:
        return ApiKeyStatus(
            is_configured=self._api_key is not None,
            masked_key=mask_api_key(self._api_key),
        )


api_key_store = InMemoryApiKeyStore()
