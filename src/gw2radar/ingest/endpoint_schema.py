from dataclasses import dataclass
from enum import Enum


class Gw2EndpointKind(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"


@dataclass(frozen=True)
class Gw2EndpointSchema:
    endpoint: str
    kind: Gw2EndpointKind
    required_permissions: frozenset[str] = frozenset()
    supports_batch: bool = False
    ttl_seconds: int = 30 * 60


ENDPOINT_SCHEMAS: dict[str, Gw2EndpointSchema] = {
    "/v2/tokeninfo": Gw2EndpointSchema(
        endpoint="/v2/tokeninfo",
        kind=Gw2EndpointKind.PRIVATE,
        required_permissions=frozenset(),
        ttl_seconds=5 * 60,
    ),
    "/v2/account": Gw2EndpointSchema(
        endpoint="/v2/account",
        kind=Gw2EndpointKind.PRIVATE,
        required_permissions=frozenset({"account"}),
    ),
    "/v2/characters": Gw2EndpointSchema(
        endpoint="/v2/characters",
        kind=Gw2EndpointKind.PRIVATE,
        required_permissions=frozenset({"characters"}),
    ),
    "/v2/account/wallet": Gw2EndpointSchema(
        endpoint="/v2/account/wallet",
        kind=Gw2EndpointKind.PRIVATE,
        required_permissions=frozenset({"wallet"}),
    ),
    "/v2/account/materials": Gw2EndpointSchema(
        endpoint="/v2/account/materials",
        kind=Gw2EndpointKind.PRIVATE,
        required_permissions=frozenset({"inventories"}),
    ),
    "/v2/account/bank": Gw2EndpointSchema(
        endpoint="/v2/account/bank",
        kind=Gw2EndpointKind.PRIVATE,
        required_permissions=frozenset({"inventories"}),
    ),
    "/v2/account/achievements": Gw2EndpointSchema(
        endpoint="/v2/account/achievements",
        kind=Gw2EndpointKind.PRIVATE,
        required_permissions=frozenset({"progression"}),
    ),
    "/v2/items": Gw2EndpointSchema(
        endpoint="/v2/items",
        kind=Gw2EndpointKind.PUBLIC,
        supports_batch=True,
        ttl_seconds=72 * 60 * 60,
    ),
    "/v2/itemstats": Gw2EndpointSchema(
        endpoint="/v2/itemstats",
        kind=Gw2EndpointKind.PUBLIC,
        supports_batch=True,
        ttl_seconds=72 * 60 * 60,
    ),
    "/v2/achievements": Gw2EndpointSchema(
        endpoint="/v2/achievements",
        kind=Gw2EndpointKind.PUBLIC,
        supports_batch=True,
        ttl_seconds=72 * 60 * 60,
    ),
    "/v2/currencies": Gw2EndpointSchema(
        endpoint="/v2/currencies",
        kind=Gw2EndpointKind.PUBLIC,
        supports_batch=True,
        ttl_seconds=72 * 60 * 60,
    ),
    "/v2/recipes": Gw2EndpointSchema(
        endpoint="/v2/recipes",
        kind=Gw2EndpointKind.PUBLIC,
        supports_batch=True,
        ttl_seconds=72 * 60 * 60,
    ),
    "/v2/commerce/prices": Gw2EndpointSchema(
        endpoint="/v2/commerce/prices",
        kind=Gw2EndpointKind.PUBLIC,
        supports_batch=True,
        ttl_seconds=30 * 60,
    ),
    "/v2/commerce/listings": Gw2EndpointSchema(
        endpoint="/v2/commerce/listings",
        kind=Gw2EndpointKind.PUBLIC,
        supports_batch=True,
        ttl_seconds=60 * 60,
    ),
    "/v2/skins": Gw2EndpointSchema(
        endpoint="/v2/skins",
        kind=Gw2EndpointKind.PUBLIC,
        supports_batch=True,
        ttl_seconds=72 * 60 * 60,
    ),
    "/v2/traits": Gw2EndpointSchema(
        endpoint="/v2/traits",
        kind=Gw2EndpointKind.PUBLIC,
        supports_batch=True,
        ttl_seconds=72 * 60 * 60,
    ),
    "/v2/skills": Gw2EndpointSchema(
        endpoint="/v2/skills",
        kind=Gw2EndpointKind.PUBLIC,
        supports_batch=True,
        ttl_seconds=72 * 60 * 60,
    ),
}


def endpoint_schema(endpoint: str) -> Gw2EndpointSchema:
    if endpoint.startswith("/v2/characters/"):
        return Gw2EndpointSchema(
            endpoint=endpoint,
            kind=Gw2EndpointKind.PRIVATE,
            required_permissions=frozenset({"characters", "inventories"}),
        )
    return ENDPOINT_SCHEMAS.get(
        endpoint,
        Gw2EndpointSchema(endpoint=endpoint, kind=Gw2EndpointKind.PUBLIC),
    )


def batch_endpoints() -> set[str]:
    return {endpoint for endpoint, schema in ENDPOINT_SCHEMAS.items() if schema.supports_batch}
