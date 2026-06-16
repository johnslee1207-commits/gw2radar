import pytest

from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_client import Gw2ApiResponse
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ingest.permission_validator import (
    Gw2PermissionError,
    TokenInfo,
    parse_tokeninfo,
    validate_endpoint_permissions,
)


class PermissionClient:
    def __init__(self, permissions):
        self.permissions = permissions
        self.calls = []

    def fetch_tokeninfo(self, api_key, *, request_id=None):
        self.calls.append(("/v2/tokeninfo", {}, api_key, request_id))
        return {"id": "token-id", "name": "Unit Test", "permissions": self.permissions}

    def get(self, endpoint, *, params=None, api_key=None, request_id=None):
        self.calls.append((endpoint, params or {}, api_key, request_id))
        return Gw2ApiResponse(endpoint=endpoint, params=params or {}, payload={"ok": True}, request_id=request_id)


def test_permission_validator_accepts_required_endpoint_scope() -> None:
    tokeninfo = parse_tokeninfo({"permissions": ["account", "wallet"]})
    validate_endpoint_permissions("/v2/account/wallet", tokeninfo)


def test_permission_validator_rejects_missing_scope() -> None:
    tokeninfo = TokenInfo(id="id", name="name", permissions=frozenset({"account"}))

    with pytest.raises(Gw2PermissionError) as exc:
        validate_endpoint_permissions("/v2/account/wallet", tokeninfo)

    assert exc.value.missing_permissions == {"wallet"}


def test_gateway_validates_private_endpoint_permissions_before_sync_call() -> None:
    client = PermissionClient(["account"])
    gateway = Gw2ApiGateway(client=client)

    result = gateway.get("/v2/account/wallet", api_key="12345678-abcdef-secret-key")

    assert result.status is GatewayStatus.PERMISSION_DENIED
    assert result.diagnostics["missing_permissions"] == ["wallet"]
    assert [call[0] for call in client.calls] == ["/v2/tokeninfo"]


def test_gateway_allows_private_endpoint_after_tokeninfo_scope_validation() -> None:
    client = PermissionClient(["account", "wallet"])
    gateway = Gw2ApiGateway(client=client)

    result = gateway.get("/v2/account/wallet", api_key="12345678-abcdef-secret-key")

    assert result.status is GatewayStatus.OK
    assert [call[0] for call in client.calls] == ["/v2/tokeninfo", "/v2/account/wallet"]
