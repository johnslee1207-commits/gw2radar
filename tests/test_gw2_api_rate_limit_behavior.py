from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_client import Gw2ApiRateLimitError
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway


class RateLimitedClient:
    def get(self, endpoint, *, params=None, api_key=None, request_id=None):
        raise Gw2ApiRateLimitError(endpoint, request_id or "unknown")


def test_private_endpoint_tokeninfo_429_uses_delayed_retry_without_ip_switching() -> None:
    gateway = Gw2ApiGateway(client=RateLimitedClient())

    result = gateway.get("/v2/account", api_key="12345678-abcdef-secret-key", priority="P1")

    assert result.status is GatewayStatus.RATE_LIMITED_RETRYING
    assert result.retry_after_seconds == 30
    delayed = gateway.queue.delayed()
    assert delayed
    assert delayed[0].endpoint == "/v2/tokeninfo"
    assert delayed[0].last_error == GatewayStatus.RATE_LIMITED_RETRYING.value
    assert "proxy" not in str(result.diagnostics).lower()
    assert "ip" not in str(result.diagnostics).lower()
