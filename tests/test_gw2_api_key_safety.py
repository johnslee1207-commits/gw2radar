from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_client import Gw2ApiClientError
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway


class FailingClient:
    def fetch_tokeninfo(self, api_key, *, request_id=None):
        return {"permissions": ["account"]}

    def get(self, endpoint, *, params=None, api_key=None, request_id=None):
        raise Gw2ApiClientError(endpoint, 500, request_id)


def test_gateway_structured_error_does_not_leak_api_key() -> None:
    raw_key = "12345678-abcdef-secret-key"
    gateway = Gw2ApiGateway(client=FailingClient())

    result = gateway.get("/v2/account", api_key=raw_key)

    assert result.status is GatewayStatus.ERROR
    assert result.diagnostics["error_code"] == "gw2_api_request_failed"
    assert raw_key not in str(result.diagnostics)
    assert raw_key not in str(result)
    assert not gateway.evidence_writer.from_api_payload(
        evidence_id="evidence:test",
        endpoint="/v2/account",
        payload={"api_key": raw_key},
    ).raw_payload["api_key"] == raw_key
