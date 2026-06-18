from enum import StrEnum

from pydantic import BaseModel, Field

from gw2radar.ingest.endpoint_schema import endpoint_schema
from gw2radar.ingest.permission_validator import TokenInfo, parse_tokeninfo


class PermissionImpactLevel(StrEnum):
    READY = "ready"
    LIMITED = "limited"
    BLOCKED = "blocked"


class PermissionFeatureImpact(BaseModel):
    feature_id: str
    label: str
    required_permissions: list[str]
    missing_permissions: list[str]
    status: PermissionImpactLevel
    player_message: str


class ApiKeyPermissionReport(BaseModel):
    schema_version: str = "gw2radar.api_key_permissions.v1"
    key_configured: bool
    token_name: str | None = None
    granted_permissions: list[str] = Field(default_factory=list)
    required_permissions: list[str] = Field(default_factory=list)
    optional_permissions: list[str] = Field(default_factory=list)
    missing_required_permissions: list[str] = Field(default_factory=list)
    missing_optional_permissions: list[str] = Field(default_factory=list)
    limited_mode: bool = True
    feature_impacts: list[PermissionFeatureImpact] = Field(default_factory=list)
    safety_boundaries: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


REQUIRED_PERMISSIONS = ["account", "characters", "inventories", "wallet", "progression"]
OPTIONAL_PERMISSIONS = ["unlocks", "builds"]

FEATURE_REQUIREMENTS = {
    "returner_diagnosis": {
        "label": "Returner Diagnosis",
        "permissions": ["account", "characters", "wallet", "inventories", "progression"],
        "message": "Needs account, character, wallet, inventory, and progression data for strongest account recovery guidance.",
    },
    "legendary_planner": {
        "label": "Legendary Planner",
        "permissions": ["account", "wallet", "inventories", "progression"],
        "message": "Needs wallet, materials, bank-style inventory, and achievement progress for missing requirements and do-not-sell guidance.",
    },
    "build_fit": {
        "label": "Build Fit Advisor",
        "permissions": ["characters", "inventories"],
        "message": "Needs character and inventory permissions for synced equipment matching; manual snapshots remain available without them.",
    },
    "market_context": {
        "label": "Market Context",
        "permissions": [],
        "message": "Market context can use public data and manual snapshots; it never requires trading permissions.",
    },
}


def required_permissions_from_private_endpoints() -> list[str]:
    endpoints = [
        "/v2/account",
        "/v2/characters",
        "/v2/account/wallet",
        "/v2/account/materials",
        "/v2/account/bank",
        "/v2/account/achievements",
    ]
    permissions = set(REQUIRED_PERMISSIONS)
    for endpoint in endpoints:
        permissions.update(endpoint_schema(endpoint).required_permissions)
    return sorted(permissions)


def build_missing_key_permission_report() -> ApiKeyPermissionReport:
    return _report_from_permissions(None, key_configured=False)


def build_permission_report(tokeninfo_payload: dict) -> ApiKeyPermissionReport:
    return _report_from_permissions(parse_tokeninfo(tokeninfo_payload), key_configured=True)


def _report_from_permissions(tokeninfo: TokenInfo | None, *, key_configured: bool) -> ApiKeyPermissionReport:
    granted = sorted(tokeninfo.permissions) if tokeninfo else []
    required = required_permissions_from_private_endpoints()
    optional = sorted(OPTIONAL_PERMISSIONS)
    missing_required = sorted(set(required).difference(granted))
    missing_optional = sorted(set(optional).difference(granted))
    return ApiKeyPermissionReport(
        key_configured=key_configured,
        token_name=tokeninfo.name if tokeninfo else None,
        granted_permissions=granted,
        required_permissions=required,
        optional_permissions=optional,
        missing_required_permissions=missing_required,
        missing_optional_permissions=missing_optional,
        limited_mode=(not key_configured) or bool(missing_required),
        feature_impacts=_feature_impacts(set(granted), key_configured=key_configured),
        safety_boundaries=[
            "Raw API keys are never returned by permission inspection.",
            "GW2Radar uses official Guild Wars 2 API token permissions only.",
            "Permission inspection does not log into the ArenaNet account or control the game client.",
            "Missing permissions enable limited mode rather than invented account facts.",
        ],
        assumptions=[] if key_configured else ["No stored API key is available, so all private-account features are limited."],
    )


def _feature_impacts(granted: set[str], *, key_configured: bool) -> list[PermissionFeatureImpact]:
    impacts: list[PermissionFeatureImpact] = []
    for feature_id, config in FEATURE_REQUIREMENTS.items():
        required = sorted(config["permissions"])
        missing = sorted(set(required).difference(granted)) if key_configured else required
        status = PermissionImpactLevel.READY if not missing else PermissionImpactLevel.LIMITED
        if required and not key_configured:
            status = PermissionImpactLevel.BLOCKED
        impacts.append(
            PermissionFeatureImpact(
                feature_id=feature_id,
                label=config["label"],
                required_permissions=required,
                missing_permissions=missing,
                status=status,
                player_message=config["message"],
            )
        )
    return impacts
