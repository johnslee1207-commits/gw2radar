from dataclasses import dataclass
import json
from typing import Any, Protocol
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from gw2radar.config.settings import get_settings
from gw2radar.ingest.security import mask_api_key


class Gw2ApiRateLimitError(Exception):
    def __init__(self, endpoint: str, request_id: str) -> None:
        super().__init__(f"GW2 API rate limited for {endpoint}; request_id={request_id}")
        self.endpoint = endpoint
        self.request_id = request_id


class Gw2ApiClientError(Exception):
    def __init__(self, endpoint: str, status_code: int, request_id: str | None = None) -> None:
        super().__init__(f"GW2 API request failed for {endpoint}; status_code={status_code}; request_id={request_id}")
        self.endpoint = endpoint
        self.status_code = status_code
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
    """Official GW2 API HTTP client skeleton.

    This class is intentionally small and conservative. It has no proxy support,
    no IP rotation, and no retry loop. Governance behavior such as cache, rate
    limiting, request queueing, and backoff belongs in Gw2ApiGateway.
    """

    def __init__(self, *, base_url: str | None = None, opener=None, timeout_seconds: float = 10.0) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.gw2_api_base_url).rstrip("/")
        self.opener = opener or urlopen
        self.timeout_seconds = timeout_seconds

    def get(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        api_key: str | None = None,
        request_id: str | None = None,
    ) -> Gw2ApiResponse:
        settings = get_settings()
        effective_key = api_key or settings.gw2_api_key
        url = self._build_url(endpoint, params or {})
        headers = {
            "Accept": "application/json",
            "User-Agent": "GW2Radar-MVP/0.1",
        }
        if request_id:
            headers["X-GW2Radar-Request-ID"] = request_id
        if effective_key:
            headers["Authorization"] = f"Bearer {effective_key}"
        request = Request(url, headers=headers, method="GET")
        try:
            with self.opener(request, timeout=self.timeout_seconds) as response:
                status_code = getattr(response, "status", 200)
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 429:
                raise Gw2ApiRateLimitError(endpoint, request_id or "unknown") from error
            raise Gw2ApiClientError(endpoint, error.code, request_id) from error
        except Exception as error:
            raise Gw2ApiClientError(endpoint, 0, request_id) from error
        return Gw2ApiResponse(
            endpoint=endpoint,
            params=params or {},
            payload=payload,
            status_code=status_code,
            request_id=request_id,
        )

    def fetch_account(self, api_key: str) -> dict:
        response = self.get("/v2/account", api_key=api_key)
        return response.payload

    def _build_url(self, endpoint: str, params: dict[str, Any]) -> str:
        path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        query = urlencode(params, doseq=False)
        return f"{self.base_url}{path}" + (f"?{query}" if query else "")

    def debug_summary(self, api_key: str | None = None) -> dict[str, str | None]:
        return {
            "base_url": self.base_url,
            "api_key": mask_api_key(api_key or get_settings().gw2_api_key),
        }
