from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, model_validator


class AcquisitionSourceType(StrEnum):
    OFFICIAL_API_PUBLIC = "official_api_public"
    OFFICIAL_API_PRIVATE = "official_api_private"
    DOWNLOADED_PDF = "downloaded_pdf"
    OFFICIAL_PATCH_NOTE = "official_patch_note"
    GW2_WIKI = "gw2_wiki"
    PUBLIC_BUILD_SITE = "public_build_site"
    COMMUNITY_SIGNAL = "community_signal"
    EXPERT_RULE = "expert_rule"
    MANUAL_NOTE = "manual_note"


class AcquisitionMode(StrEnum):
    API = "api"
    LOCAL_FILE = "local_file"
    MANUAL = "manual"
    WEB_SUMMARY = "web_summary"


class AllowedUse(StrEnum):
    API_JSON = "api_json"
    SUMMARY_AND_REFERENCE = "summary_and_reference"
    MANUAL_NOTE = "manual_note"
    METADATA_ONLY = "metadata_only"


class GraphTarget(StrEnum):
    PUBLIC_GAME = "public_game"
    PRIVATE_PLAYER_STATE = "private_player_state"
    PERSONAL_INTELLIGENCE = "personal_intelligence"
    NONE = "none"


class KbTarget(StrEnum):
    OFFICIAL = "official"
    LEGENDARY = "legendary"
    RETURNER = "returner"
    BUILD = "build"
    MARKET = "market"
    GUILD = "guild"
    CREATOR = "creator"
    NONE = "none"


class RefreshMode(StrEnum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT_DRIVEN = "event_driven"
    USER_TRIGGERED = "user_triggered"


class FreshnessStatus(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    EXPIRED = "expired"
    UNKNOWN = "unknown"
    DEPRECATED = "deprecated"


class AcquisitionJobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DELAYED = "delayed"
    SKIPPED = "skipped"


class AcquisitionPriority(StrEnum):
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class ContentType(StrEnum):
    API_JSON = "api_json"
    HTML = "html"
    PDF = "pdf"
    MARKDOWN = "markdown"
    MANUAL_NOTE = "manual_note"


class ReviewStatus(StrEnum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    DEPRECATED = "deprecated"
    NEEDS_UPDATE = "needs_update"


class AcquisitionSourceInput(BaseModel):
    name: str = Field(min_length=1)
    source_type: AcquisitionSourceType
    acquisition_mode: AcquisitionMode
    base_url: HttpUrl | None = None
    local_path: str | None = None
    allowed_use: AllowedUse
    graph_target: GraphTarget = GraphTarget.NONE
    kb_target: KbTarget = KbTarget.NONE
    trust_level: float = Field(default=0.7, ge=0.0, le=1.0)
    review_required: bool = True
    enabled: bool = True
    notes: str | None = None

    @model_validator(mode="after")
    def validate_source_contract(self) -> "AcquisitionSourceInput":
        if self.source_type == AcquisitionSourceType.OFFICIAL_API_PRIVATE:
            if self.graph_target != GraphTarget.PRIVATE_PLAYER_STATE:
                raise ValueError("Private official API sources must target the private player state graph.")
            if self.allowed_use != AllowedUse.API_JSON:
                raise ValueError("Private official API sources can only use API JSON.")
        if self.acquisition_mode == AcquisitionMode.LOCAL_FILE and not self.local_path:
            raise ValueError("Local file acquisition sources require local_path.")
        if self.acquisition_mode == AcquisitionMode.API and self.base_url is None:
            raise ValueError("API acquisition sources require base_url.")
        if self.source_type in {AcquisitionSourceType.COMMUNITY_SIGNAL, AcquisitionSourceType.PUBLIC_BUILD_SITE}:
            self.review_required = True
        return self


class AcquisitionSource(AcquisitionSourceInput):
    source_id: str
    review_status: ReviewStatus = ReviewStatus.DRAFT
    created_at: datetime
    updated_at: datetime


class SourcePolicyInput(BaseModel):
    allowed_use: AllowedUse
    refresh_mode: RefreshMode = RefreshMode.MANUAL
    refresh_interval_seconds: int | None = Field(default=None, ge=60)
    freshness_required_for_strong_action: bool = True
    can_drive_paid_report: bool = False
    can_drive_strong_recommendation: bool = False
    retain_raw_evidence: bool = False
    forbidden_use: list[str] = Field(default_factory=lambda: ["full_text_copy", "automated_trade"])
    attribution_required: bool = True

    @model_validator(mode="after")
    def validate_policy_contract(self) -> "SourcePolicyInput":
        forbidden = {item.lower() for item in self.forbidden_use}
        blocked = {"proxy_pool", "ip_rotation", "automatic_trade", "automated_trade_execution"}
        if forbidden & blocked:
            raise ValueError("Source policies cannot permit proxy rotation or automated trading behavior.")
        if self.refresh_mode == RefreshMode.SCHEDULED and self.refresh_interval_seconds is None:
            raise ValueError("Scheduled source policies require refresh_interval_seconds.")
        if self.allowed_use in {AllowedUse.METADATA_ONLY, AllowedUse.MANUAL_NOTE}:
            self.can_drive_strong_recommendation = False
        return self


class SourcePolicy(SourcePolicyInput):
    policy_id: str
    source_id: str
    created_at: datetime
    updated_at: datetime


class AcquisitionJobInput(BaseModel):
    source_id: str
    job_type: str = "refresh"
    priority: AcquisitionPriority = AcquisitionPriority.P3
    params: dict[str, Any] = Field(default_factory=dict)
    requested_by: str = "system"

    @model_validator(mode="after")
    def validate_no_secret_params(self) -> "AcquisitionJobInput":
        _ensure_no_sensitive_params(self.params)
        return self


class AcquisitionJob(AcquisitionJobInput):
    job_id: str
    status: AcquisitionJobStatus
    attempts: int = 0
    max_attempts: int = 3
    worker_id: str | None = None
    leased_until: datetime | None = None
    next_attempt_at: datetime | None = None
    last_error_code: str | None = None
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class RawEvidenceInput(BaseModel):
    source_id: str
    job_id: str | None = None
    content_type: ContentType
    title: str
    source_url: str | None = None
    payload_ref: str | None = None
    payload_hash: str | None = None
    summary: str = Field(default="", max_length=1200)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_evidence_contract(self) -> "RawEvidenceInput":
        if self.content_type == ContentType.PDF and not self.payload_ref:
            raise ValueError("PDF evidence must use payload_ref instead of storing copied full text.")
        _ensure_no_sensitive_params(self.metadata)
        return self


class RawEvidence(RawEvidenceInput):
    evidence_id: str
    created_at: datetime


class ActionEligibility(BaseModel):
    can_drive_strong_recommendation: bool
    can_drive_paid_report: bool
    reason_codes: list[str] = Field(default_factory=list)


class SourceHealth(BaseModel):
    source_id: str
    freshness_status: FreshnessStatus
    latest_job_status: AcquisitionJobStatus | None = None
    last_checked_at: datetime | None = None
    last_success_at: datetime | None = None
    last_error_code: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    action_eligibility: ActionEligibility
    review_status: ReviewStatus
    enabled: bool


SENSITIVE_PARAM_MARKERS = {
    "api_key",
    "apikey",
    "access_token",
    "authorization",
    "bearer",
    "password",
    "secret",
    "token",
    "proxy",
    "proxy_url",
    "ip_rotation",
}


def _ensure_no_sensitive_params(value: Any, path: str = "params") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in SENSITIVE_PARAM_MARKERS):
                raise ValueError(f"Acquisition job parameters cannot store sensitive or proxy fields: {path}.{key}")
            _ensure_no_sensitive_params(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _ensure_no_sensitive_params(item, f"{path}[{index}]")
    elif isinstance(value, str):
        lowered = value.lower()
        if lowered.startswith("bearer ") or "api_key=" in lowered or "access_token=" in lowered:
            raise ValueError("Acquisition job parameters cannot store secret-bearing values.")
