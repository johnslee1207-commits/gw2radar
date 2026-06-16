from dataclasses import dataclass
from typing import Any, Protocol


class Gw2ApiRateLimitError(Exception):
    def __init__(self, endpoint: str, request_id: str) -> None:
        super().__init__(f"GW2 API rate limited for {endpoint}; request_id={request_id}")
        self.endpoint = endpoint
        self.request_id = request_id


@dataclass(frozen=True)
class Gw2ApiResponse:
    endpoint: str
    params: dict[str, Any]
    payload: Any
    status_code: int = 200
    request_id: str | None = None


class Gw2ApiClientProtocol(Protocol):
    def get(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        api_key: str | None = None,
        request_id: str | None = None,
    ) -> Gw2ApiResponse:
        ...


class GW2ApiClient:
    """Future official GW2 API client.

    MVP 0.1 keeps this as an inert skeleton. All real external API access must
    be introduced through Gw2ApiGateway, never through business modules.
    """

    def get(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        api_key: str | None = None,
        request_id: str | None = None,
    ) -> Gw2ApiResponse:
        raise NotImplementedError("Real GW2 API integration is outside MVP 0.1.")

    def fetch_account(self, api_key: str) -> dict:
        raise NotImplementedError("Real GW2 API integration is outside MVP 0.1.")
