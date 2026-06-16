from dataclasses import dataclass
from typing import Any

from gw2radar.ingest.endpoint_schema import endpoint_schema


@dataclass(frozen=True)
class TokenInfo:
    id: str | None
    name: str | None
    permissions: frozenset[str]


class Gw2PermissionError(Exception):
    def __init__(self, endpoint: str, missing_permissions: set[str]) -> None:
        self.endpoint = endpoint
        self.missing_permissions = missing_permissions
        missing = ",".join(sorted(missing_permissions))
        super().__init__(f"GW2 API token lacks required permissions for {endpoint}: {missing}")


def parse_tokeninfo(payload: dict[str, Any]) -> TokenInfo:
    permissions = payload.get("permissions") or []
    return TokenInfo(
        id=payload.get("id"),
        name=payload.get("name"),
        permissions=frozenset(str(permission) for permission in permissions),
    )


def validate_endpoint_permissions(endpoint: str, tokeninfo: TokenInfo | dict[str, Any]) -> None:
    schema = endpoint_schema(endpoint)
    if not schema.required_permissions:
        return
    token = parse_tokeninfo(tokeninfo) if isinstance(tokeninfo, dict) else tokeninfo
    missing = set(schema.required_permissions.difference(token.permissions))
    if missing:
        raise Gw2PermissionError(endpoint, missing)
