from pydantic import BaseModel, Field

from gw2radar.config.settings import Settings
from gw2radar.security.deployment_mode import DeploymentMode


class WorkspaceSkeleton(BaseModel):
    schema_version: str = "gw2radar.workspace_skeleton.v1"
    workspace_id: str
    owner_user_id: str
    mode: str
    persistence_scope: str
    team_credential_sharing_enabled: bool = False
    private_data_isolation: str = "single local user boundary in MVP; tenant isolation is a later explicit migration."


class AuthSessionSkeleton(BaseModel):
    schema_version: str = "gw2radar.auth_session_skeleton.v1"
    auth_required: bool
    session_backend: str
    current_user_id: str
    supported_states: list[str] = Field(default_factory=list)
    deferred: list[str] = Field(default_factory=list)


class InfrastructureAdapterPlan(BaseModel):
    schema_version: str = "gw2radar.infrastructure_adapter_plan.v1"
    postgres: dict
    redis: dict
    object_storage: dict
    billing_guard: dict


class ProductionSaasFoundation(BaseModel):
    schema_version: str = "gw2radar.production_saas_foundation.v1"
    deployment_mode: str
    ready_for_hosted_saas: bool
    local_first_supported: bool
    workspace: WorkspaceSkeleton
    auth_session: AuthSessionSkeleton
    adapters: InfrastructureAdapterPlan
    missing_gates: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_boundaries: list[str] = Field(default_factory=list)
    deferred_capabilities: list[str] = Field(default_factory=list)


def build_production_saas_foundation(settings: Settings) -> ProductionSaasFoundation:
    mode = DeploymentMode(settings.deployment_mode)
    missing_gates = _missing_gates(settings, mode)
    blockers = _blockers(settings, mode)
    return ProductionSaasFoundation(
        deployment_mode=mode.value,
        ready_for_hosted_saas=mode is DeploymentMode.HOSTED_SAAS and not missing_gates and not blockers,
        local_first_supported=True,
        workspace=_workspace_skeleton(mode),
        auth_session=_auth_session_skeleton(mode),
        adapters=_adapter_plan(settings, mode),
        missing_gates=missing_gates,
        blockers=blockers,
        next_actions=_next_actions(mode, missing_gates, blockers),
        safety_boundaries=[
            "Local-first mode remains supported and does not require hosted SaaS services.",
            "Hosted SaaS behavior must stay behind deployment_mode=hosted_saas.",
            "Private player data must remain isolated by user/workspace boundary before real multi-tenant launch.",
            "Real billing and team workspace credential sharing remain deferred until explicit production stages.",
        ],
        deferred_capabilities=[
            "full multi-tenant SaaS launch",
            "real payment provider",
            "team workspace credential sharing",
            "external KMS vault",
            "autonomous agents",
        ],
    )


def _workspace_skeleton(mode: DeploymentMode) -> WorkspaceSkeleton:
    return WorkspaceSkeleton(
        workspace_id="local-workspace" if mode is not DeploymentMode.HOSTED_SAAS else "hosted-workspace-placeholder",
        owner_user_id="local-user",
        mode="single_user_local" if mode is not DeploymentMode.HOSTED_SAAS else "hosted_saas_placeholder",
        persistence_scope="sqlite_local" if mode is not DeploymentMode.HOSTED_SAAS else "postgres_planned",
    )


def _auth_session_skeleton(mode: DeploymentMode) -> AuthSessionSkeleton:
    if mode is DeploymentMode.HOSTED_SAAS:
        return AuthSessionSkeleton(
            auth_required=True,
            session_backend="redis_planned",
            current_user_id="local-user",
            supported_states=["anonymous_blocked", "authenticated_placeholder"],
            deferred=["real identity provider", "session cookie hardening", "workspace role enforcement"],
        )
    return AuthSessionSkeleton(
        auth_required=False,
        session_backend="local_process",
        current_user_id="local-user",
        supported_states=["local_user"],
        deferred=["hosted identity provider"],
    )


def _adapter_plan(settings: Settings, mode: DeploymentMode) -> InfrastructureAdapterPlan:
    database_url = settings.database_url
    postgres_ready = database_url.startswith("postgresql://") or database_url.startswith("postgresql+")
    redis_ready = bool(settings.redis_url)
    object_storage_ready = settings.object_storage_backend != "local_filesystem"
    billing_guard_ready = settings.billing_provider == "mock"
    return InfrastructureAdapterPlan(
        postgres={
            "status": "configured" if postgres_ready else "planned",
            "database_url_kind": "postgresql" if postgres_ready else "sqlite_or_other",
            "required_for_hosted_saas": mode is DeploymentMode.HOSTED_SAAS,
        },
        redis={
            "status": "configured" if redis_ready else "planned",
            "required_for_hosted_saas": mode is DeploymentMode.HOSTED_SAAS,
            "uses": ["session cache", "worker queue coordination", "rate-limit metadata"],
        },
        object_storage={
            "status": "configured" if object_storage_ready else "local_filesystem",
            "backend": settings.object_storage_backend,
            "required_for_hosted_saas": mode is DeploymentMode.HOSTED_SAAS,
        },
        billing_guard={
            "status": "mock_only" if billing_guard_ready else "unsupported_provider_configured",
            "provider": settings.billing_provider,
            "real_payment_enabled": False,
            "required_boundary": "real billing remains deferred; entitlement tests use mock provider only",
        },
    )


def _missing_gates(settings: Settings, mode: DeploymentMode) -> list[str]:
    if mode is not DeploymentMode.HOSTED_SAAS:
        return []
    gates: list[str] = []
    if not (
        settings.database_url.startswith("postgresql://")
        or settings.database_url.startswith("postgresql+")
    ):
        gates.append("PostgreSQL database_url is required for hosted SaaS readiness.")
    if not settings.redis_url:
        gates.append("Redis URL is required for hosted sessions and queue coordination.")
    if settings.object_storage_backend == "local_filesystem":
        gates.append("Object storage backend must be configured before hosted artifact delivery.")
    return gates


def _blockers(settings: Settings, mode: DeploymentMode) -> list[str]:
    blockers: list[str] = []
    if mode is DeploymentMode.HOSTED_SAAS and settings.billing_provider != "mock":
        blockers.append("Real billing provider is configured but Phase E allows mock billing guard only.")
    return blockers


def _next_actions(mode: DeploymentMode, missing_gates: list[str], blockers: list[str]) -> list[str]:
    if mode is DeploymentMode.HOSTED_SAAS and (missing_gates or blockers):
        return [
            "Configure PostgreSQL, Redis, and object storage adapters behind deployment mode.",
            "Keep billing provider set to mock until the real payment stage is explicitly approved.",
            "Add workspace role enforcement before exposing team data.",
        ]
    return [
        "Keep local-first mode as the default development path.",
        "Use this readiness contract before enabling hosted SaaS deployment.",
        "Implement production adapters in separate, test-gated slices.",
    ]
