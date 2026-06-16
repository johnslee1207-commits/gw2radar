import pytest

from gw2radar.ingest.endpoint_schema import batch_endpoints, endpoint_schema
from gw2radar.ingest.gw2_api_client import Gw2ApiResponse
from gw2radar.ingest.gw2_api_gateway import BATCH_ENDPOINTS, Gw2ApiGateway


class RecordingClient:
    def __init__(self) -> None:
        self.calls = []

    def get(self, endpoint, *, params=None, api_key=None, request_id=None):
        self.calls.append((endpoint, params or {}))
        return Gw2ApiResponse(endpoint=endpoint, params=params or {}, payload={"ok": True})


def test_endpoint_schema_marks_official_batch_endpoints() -> None:
    assert "/v2/items" in batch_endpoints()
    assert endpoint_schema("/v2/items").supports_batch is True
    assert endpoint_schema("/v2/account").supports_batch is False


def test_gateway_batch_helper_uses_endpoint_schema_set() -> None:
    assert BATCH_ENDPOINTS == batch_endpoints()
    gateway = Gw2ApiGateway(client=RecordingClient())

    result = gateway.get_batch("/v2/achievements", ids=[3, 1, 2])

    assert result.status.value == "ok"
    assert gateway.client.calls[0][1]["ids"] == "3,1,2"


def test_gateway_batch_helper_rejects_private_endpoint() -> None:
    with pytest.raises(ValueError):
        Gw2ApiGateway(client=RecordingClient()).get_batch("/v2/account", ids=[1])
