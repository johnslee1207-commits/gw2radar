from io import BytesIO
from urllib.error import HTTPError

import pytest

from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_client import GW2ApiClient, Gw2ApiClientError, Gw2ApiRateLimitError
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway


class FakeResponse:
    status = 200

    def __init__(self, payload: bytes = b'{"ok": true}') -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


class RecordingOpener:
    def __init__(self, response=None, error: Exception | None = None) -> None:
        self.response = response or FakeResponse()
        self.error = error
        self.requests = []

    def __call__(self, request, timeout: float):
        self.requests.append((request, timeout))
        if self.error:
            raise self.error
        return self.response


def test_client_builds_safe_request_without_key_in_url() -> None:
    opener = RecordingOpener()
    client = GW2ApiClient(base_url="https://example.test", opener=opener)

    response = client.get(
        "/v2/items",
        params={"ids": "1,2,3"},
        api_key="12345678-abcdef-secret-key",
        request_id="req-1",
    )

    request, timeout = opener.requests[0]
    assert response.payload == {"ok": True}
    assert timeout == 10.0
    assert request.full_url == "https://example.test/v2/items?ids=1%2C2%2C3"
    assert "12345678-abcdef-secret-key" not in request.full_url
    assert request.headers["Authorization"] == "Bearer 12345678-abcdef-secret-key"
    assert request.headers["X-gw2radar-request-id"] == "req-1"


def test_client_429_raises_rate_limit_without_key_leak() -> None:
    error = HTTPError(
        url="https://example.test/v2/account",
        code=429,
        msg="Too Many Requests",
        hdrs={},
        fp=BytesIO(b"{}"),
    )
    client = GW2ApiClient(base_url="https://example.test", opener=RecordingOpener(error=error))

    with pytest.raises(Gw2ApiRateLimitError) as exc:
        client.get("/v2/account", api_key="12345678-abcdef-secret-key", request_id="req-429")

    assert "12345678-abcdef-secret-key" not in str(exc.value)
    assert exc.value.request_id == "req-429"


def test_client_non_429_error_masks_context() -> None:
    error = HTTPError(
        url="https://example.test/v2/account",
        code=500,
        msg="Server Error",
        hdrs={},
        fp=BytesIO(b"{}"),
    )
    client = GW2ApiClient(base_url="https://example.test", opener=RecordingOpener(error=error))

    with pytest.raises(Gw2ApiClientError) as exc:
        client.get("/v2/account", api_key="12345678-abcdef-secret-key", request_id="req-500")

    assert "12345678-abcdef-secret-key" not in str(exc.value)
    assert exc.value.status_code == 500


def test_gateway_can_wrap_real_client_skeleton_with_fake_transport() -> None:
    opener = RecordingOpener()
    client = GW2ApiClient(base_url="https://example.test", opener=opener)
    gateway = Gw2ApiGateway(client=client)

    result = gateway.get_batch("/v2/items", ids=[1, 2, 3], api_key="12345678-abcdef-secret-key")

    assert result.status is GatewayStatus.OK
    assert len(opener.requests) == 1
    request, _timeout = opener.requests[0]
    assert "/v2/items?ids=1%2C2%2C3" in request.full_url
    assert "12345678-abcdef-secret-key" not in request.full_url
