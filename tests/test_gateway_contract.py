from typing import Any

import pytest

from gw2radar.ingest.cache_store import endpoint_ttl_seconds
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_client import Gw2ApiResponse
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ingest.rate_limiter import TokenBucketRateLimiter


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        api_key: str | None = None,
        request_id: str | None = None,
    ) -> Gw2ApiResponse:
        self.calls.append((endpoint, params or {}))
        return Gw2ApiResponse(endpoint=endpoint, params=params or {}, payload={"ok": True})


def test_gateway_status_is_enum() -> None:
    client = RecordingClient()
    gateway = Gw2ApiGateway(client=client)

    result = gateway.get("/v2/items", params={"ids": "1,2"})

    assert result.status is GatewayStatus.OK


def test_endpoint_ttl_resolver_uses_governed_defaults() -> None:
    assert endpoint_ttl_seconds("/v2/items") == 72 * 60 * 60
    assert endpoint_ttl_seconds("/v2/account") == 30 * 60
    assert endpoint_ttl_seconds("/v2/unknown") == 30 * 60


def test_batch_helper_uses_single_supported_request() -> None:
    client = RecordingClient()
    gateway = Gw2ApiGateway(client=client)

    result = gateway.get_batch("/v2/items", ids=[1, 2, 3])

    assert result.status is GatewayStatus.OK
    assert len(client.calls) == 1
    endpoint, params = client.calls[0]
    assert endpoint == "/v2/items"
    assert params["ids"] == "1,2,3"
    assert params["batch_count"] == 3


def test_batch_helper_rejects_unsupported_endpoint_and_empty_ids() -> None:
    gateway = Gw2ApiGateway(client=RecordingClient())

    with pytest.raises(ValueError):
        gateway.get_batch("/v2/account", ids=[1])
    with pytest.raises(ValueError):
        gateway.get_batch("/v2/items", ids=[])


def test_refresh_pending_records_retry_metadata() -> None:
    limiter = TokenBucketRateLimiter(burst_capacity=0, refill_rate_per_second=0, hard_max_per_minute=0)
    gateway = Gw2ApiGateway(client=RecordingClient(), limiter=limiter)

    result = gateway.get("/v2/items", params={"ids": "1"})

    assert result.status is GatewayStatus.REFRESH_PENDING
    delayed = gateway.queue.delayed()
    assert delayed[0].retry_after_seconds == 15
    assert delayed[0].last_error == GatewayStatus.REFRESH_PENDING.value
