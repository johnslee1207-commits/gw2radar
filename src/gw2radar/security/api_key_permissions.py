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


class ApiKeyAnalysisModule(BaseModel):
    module_id: str
    label: str
    required_permissions: list[str]
    missing_permissions: list[str]
    status: PermissionImpactLevel
    player_message: str


class ApiKeyValueAnalysisReadiness(BaseModel):
    status: PermissionImpactLevel
    ready_module_count: int = 0
    blocked_module_count: int = 0
    limited_module_count: int = 0
    player_message: str
    missing_permissions: list[str] = Field(default_factory=list)


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
    unlocked_analysis_modules: list[ApiKeyAnalysisModule] = Field(default_factory=list)
    blocked_analysis_modules: list[ApiKeyAnalysisModule] = Field(default_factory=list)
    value_analysis_readiness: ApiKeyValueAnalysisReadiness | None = None
    safety_boundaries: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


REQUIRED_PERMISSIONS = ["account", "characters", "inventories", "wallet", "progression"]
OPTIONAL_PERMISSIONS = ["unlocks", "builds", "tradingpost"]

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

VALUE_ANALYSIS_MODULES = {
    "account_overview": {
        "label": "Account Overview",
        "permissions": ["account"],
        "message": "Unlocks account name, world, age, AP, fractal, and WvW rank context.",
    },
    "wallet_value": {
        "label": "Wallet Value",
        "permissions": ["wallet"],
        "message": "Unlocks liquid coin and currency context for goal planning.",
    },
    "material_value": {
        "label": "Material Storage Value",
        "permissions": ["inventories"],
        "message": "Unlocks material storage holdings for legendary, market, and do-not-sell analysis.",
    },
    "bank_value": {
        "label": "Bank And Shared Inventory Value",
        "permissions": ["inventories"],
        "message": "Unlocks bank-style holdings for value and missing-item analysis.",
    },
    "character_inventory_and_gear": {
        "label": "Character Inventory And Gear",
        "permissions": ["characters", "inventories"],
        "message": "Unlocks character equipment and inventory context for Build Fit and transition cost analysis.",
    },
    "tradingpost_orders": {
        "label": "Trading Post Orders",
        "permissions": ["tradingpost"],
        "message": "Unlocks current buy and sell order context when the key includes tradingpost access.",
    },
    "build_templates": {
        "label": "Build Templates",
        "permissions": ["builds"],
        "message": "Unlocks saved build-template context when available; manual build import remains supported.",
    },
    "progression_routes": {
        "label": "Progression And Routes",
        "permissions": ["progression"],
        "message": "Unlocks achievement and progression context for route planning and returner guidance.",
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
    analysis_modules = _analysis_modules(set(granted), key_configured=key_configured)
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
        unlocked_analysis_modules=[module for module in analysis_modules if module.status is PermissionImpactLevel.READY],
        blocked_analysis_modules=[module for module in analysis_modules if module.status is not PermissionImpactLevel.READY],
        value_analysis_readiness=_value_analysis_readiness(analysis_modules, key_configured=key_configured),
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


def _analysis_modules(granted: set[str], *, key_configured: bool) -> list[ApiKeyAnalysisModule]:
    modules: list[ApiKeyAnalysisModule] = []
    for module_id, config in VALUE_ANALYSIS_MODULES.items():
        required = sorted(config["permissions"])
        missing = sorted(set(required).difference(granted)) if key_configured else required
        status = PermissionImpactLevel.READY if not missing else PermissionImpactLevel.BLOCKED
        if missing and key_configured and set(missing) != set(required):
            status = PermissionImpactLevel.LIMITED
        modules.append(
            ApiKeyAnalysisModule(
                module_id=module_id,
                label=config["label"],
                required_permissions=required,
                missing_permissions=missing,
                status=status,
                player_message=config["message"],
            )
        )
    return modules


def _value_analysis_readiness(
    modules: list[ApiKeyAnalysisModule],
    *,
    key_configured: bool,
) -> ApiKeyValueAnalysisReadiness:
    ready = [module for module in modules if module.status is PermissionImpactLevel.READY]
    limited = [module for module in modules if module.status is PermissionImpactLevel.LIMITED]
    blocked = [module for module in modules if module.status is PermissionImpactLevel.BLOCKED]
    missing = sorted({permission for module in blocked + limited for permission in module.missing_permissions})
    if not key_configured:
        status = PermissionImpactLevel.BLOCKED
        message = "No stored API key is available, so account value analysis cannot run yet."
    elif blocked or limited:
        status = PermissionImpactLevel.LIMITED
        message = "Account value analysis can run in limited mode; missing permissions will be shown as coverage gaps."
    else:
        status = PermissionImpactLevel.READY
        message = "Account value analysis is ready for all currently modeled modules."
    return ApiKeyValueAnalysisReadiness(
        status=status,
        ready_module_count=len(ready),
        blocked_module_count=len(blocked),
        limited_module_count=len(limited),
        player_message=message,
        missing_permissions=missing,
    )
