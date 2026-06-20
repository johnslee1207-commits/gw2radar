from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Literal, Protocol
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from pydantic import BaseModel, Field, ValidationError


RouteStepType = Literal["achievement", "collection"]
RouteTimeGate = Literal["daily", "weekly", "none"]
RouteSourceStatus = Literal["reviewed", "draft", "disabled"]
RouteAccountProgressStatus = Literal["unknown", "not_started", "in_progress", "complete"]
RouteRemediationReviewStatus = Literal["acknowledged", "resolved", "deferred"]


ACHIEVEMENT_ROUTE_SOURCE_ROOT = Path("docs/knowledge_base/achievement_routes")
ACHIEVEMENT_ROUTE_AUDIT_ROOT = Path("data/achievement_route_audit")
ACHIEVEMENT_ROUTE_RELEASE_EXPORT_ROOT = Path("src/gw2radar/reports/artifacts/achievement_route_release_exports")


class AchievementRouteRequest(BaseModel):
    user_id: str = "local-user"
    goal_id: str = "aurora_sample"
    available_minutes: int = Field(default=45, ge=10, le=240)
    completed_step_ids: list[str] = Field(default_factory=list)
    unlocked_prerequisite_ids: list[str] = Field(default_factory=list)
    include_group_content: bool = False


class AchievementRouteStep(BaseModel):
    step_id: str
    title: str
    step_type: RouteStepType
    map_name: str
    region: str
    objective: str
    advances_goal_id: str
    prerequisite_ids: list[str] = Field(default_factory=list)
    time_gate: RouteTimeGate = "none"
    estimated_minutes: int = Field(ge=1)
    group_required: bool = False
    evidence_refs: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    source_id: str = "kb:seed:legendary-route:v1"
    source_status: RouteSourceStatus = "reviewed"
    official_achievement_id: int | None = None
    account_progress_status: RouteAccountProgressStatus = "unknown"
    account_progress_note: str | None = None


class AchievementRouteSegment(BaseModel):
    segment_id: str
    map_name: str
    region: str
    ready_step_ids: list[str]
    blocked_step_ids: list[str]
    time_gated_step_ids: list[str]
    total_ready_minutes: int
    notes: list[str] = Field(default_factory=list)


class AchievementRouteAction(BaseModel):
    action_id: str
    action_type: Literal["run_segment", "unlock_prerequisite", "do_time_gated_step", "postpone_blocked_step"]
    title: str
    step_ids: list[str]
    reason: str
    manual_only: bool = True


class AchievementRoutePlan(BaseModel):
    schema_version: str = "gw2radar.achievement_route_plan.v1"
    route_id: str
    user_id: str
    goal_id: str
    generated_at: datetime
    available_minutes: int
    steps: list[AchievementRouteStep]
    segments: list[AchievementRouteSegment]
    ready_step_ids: list[str]
    blocked_step_ids: list[str]
    time_gated_step_ids: list[str]
    next_actions: list[AchievementRouteAction]
    source_ids: list[str]
    source_warnings: list[str]
    assumptions: list[str]
    safety_boundaries: list[str]


class AchievementRouteSourceManifest(BaseModel):
    schema_version: str = "gw2radar.achievement_route_source.v1"
    source_id: str
    title: str
    source_status: RouteSourceStatus = "reviewed"
    source_url: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    reviewed_by: str
    reviewed_at: str
    assumptions: list[str] = Field(default_factory=list)
    steps: list[AchievementRouteStep]


class AchievementRouteSourceSummary(BaseModel):
    source_id: str
    title: str
    source_status: RouteSourceStatus
    source_url: str | None = None
    source_refs: list[str] = Field(default_factory=list)
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    step_count: int = 0
    warning: str | None = None


class OfficialAchievementDetail(BaseModel):
    id: int
    name: str
    description: str | None = None
    requirement: str | None = None
    locked_text: str | None = None
    type: str | None = None
    flags: list[str] = Field(default_factory=list)
    bits: list[dict] = Field(default_factory=list)


class OfficialAccountAchievementProgress(BaseModel):
    id: int
    current: int | None = None
    max: int | None = None
    done: bool | None = None


class OfficialAchievementRoutePreviewRequest(BaseModel):
    source_id: str = "official:achievement-route-preview"
    title: str = "Official achievement route preview"
    goal_id: str = "custom_achievement_route"
    reviewed_by: str = "operator_review_required"
    achievement_details: list[OfficialAchievementDetail]
    account_achievements: list[OfficialAccountAchievementProgress] = Field(default_factory=list)
    source_refs: list[str] = Field(
        default_factory=lambda: [
            "official:/v2/achievements",
            "official:/v2/account/achievements",
        ]
    )


class OfficialAchievementRoutePreview(BaseModel):
    schema_version: str = "gw2radar.official_achievement_route_preview.v1"
    manifest: AchievementRouteSourceManifest
    source_summary: AchievementRouteSourceSummary
    candidate_step_count: int
    completed_step_ids: list[str]
    warnings: list[str]


class OfficialAchievementFetchPreviewRequest(BaseModel):
    source_id: str = "official:achievement-route-fetch-preview"
    title: str = "Official achievement fetch preview"
    goal_id: str = "custom_achievement_route"
    reviewed_by: str = "operator_review_required"
    achievement_ids: list[int] = Field(min_length=1, max_length=200)
    account_achievements: list[OfficialAccountAchievementProgress] = Field(default_factory=list)
    use_stored_account_progress: bool = False


class OfficialAchievementFetchPreview(BaseModel):
    schema_version: str = "gw2radar.official_achievement_fetch_preview.v1"
    preview: OfficialAchievementRoutePreview
    requested_achievement_ids: list[int]
    fetched_achievement_ids: list[int]
    missing_achievement_ids: list[int]
    gateway_statuses: dict[str, str]
    warnings: list[str]


class AchievementRouteReviewedPromotionRequest(BaseModel):
    confirmed_reviewed: bool = False
    reviewer: str = Field(min_length=2)
    reviewed_source_id: str | None = None
    review_notes: list[str] = Field(default_factory=list)
    overwrite_existing: bool = False


class AchievementRouteReviewedPromotionResult(BaseModel):
    schema_version: str = "gw2radar.achievement_route_reviewed_promotion.v1"
    manifest: AchievementRouteSourceManifest
    manifest_path: str
    source_summary: AchievementRouteSourceSummary
    planner_ingestion_status: Literal["ready", "blocked"]
    warnings: list[str]


class AchievementRoutePromotionAuditRecord(BaseModel):
    schema_version: str = "gw2radar.achievement_route_promotion_audit.v1"
    event_id: str
    action: Literal["promote_reviewed"]
    occurred_at: datetime
    reviewer: str
    source_id: str
    source_status: RouteSourceStatus
    manifest_path: str
    requested_achievement_ids: list[int]
    fetched_achievement_ids: list[int]
    missing_achievement_ids: list[int]
    candidate_step_count: int
    review_notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    planner_ingestion_status: Literal["ready", "blocked"]
    safety_boundary: str = "Reviewed route promotion audit stores metadata only; no raw API key or private account payload is persisted."


class AchievementRoutePromotionAuditList(BaseModel):
    schema_version: str = "gw2radar.achievement_route_promotion_audit_list.v1"
    records: list[AchievementRoutePromotionAuditRecord]
    filters: dict[str, str | int | None]
    boundary: str = "Promotion audit exports are metadata-only and must not contain raw API keys or private account payloads."


class AchievementRouteReleaseReadiness(BaseModel):
    schema_version: str = "gw2radar.achievement_route_release_readiness.v1"
    ready: bool
    maturity_label: Literal["blocked", "review_needed", "ready"]
    readiness_score: float
    reviewed_source_count: int
    reviewed_step_count: int
    promotion_audit_count: int
    promoted_source_count: int
    audited_source_ids: list[str]
    unaudited_reviewed_source_ids: list[str]
    missing_achievement_ids: list[int]
    blockers: list[str]
    warnings: list[str]
    next_steps: list[str]
    evidence_chain: list[str]
    boundary: str = "Release readiness is an operator gate for manual planning content; it does not automate gameplay, trading, or account changes."


class AchievementRouteStepQuality(BaseModel):
    step_id: str
    source_id: str
    title: str
    official_achievement_id: int | None = None
    quality_score: float
    evidence_complete: bool
    map_inference_risk: Literal["low", "medium", "high"]
    time_gate_risk: Literal["low", "medium", "high"]
    missing_official_id: bool
    review_flags: list[str] = Field(default_factory=list)
    remediation: list[str] = Field(default_factory=list)


class AchievementRouteSourceQuality(BaseModel):
    source_id: str
    title: str
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    step_count: int
    average_quality_score: float
    high_risk_step_count: int
    evidence_gap_count: int
    map_inference_risk_count: int
    time_gate_risk_count: int


class AchievementRouteSourceQualityReview(BaseModel):
    schema_version: str = "gw2radar.achievement_route_source_quality.v1"
    overall_score: float
    maturity_label: Literal["blocked", "review_needed", "ready"]
    source_reviews: list[AchievementRouteSourceQuality]
    step_reviews: list[AchievementRouteStepQuality]
    missing_achievement_ids: list[int]
    remediation: list[str]
    boundary: str = "Source quality review is advisory metadata for human route reviewers; it does not certify current in-game availability."


class AchievementRouteRemediationItem(BaseModel):
    item_id: str
    priority: Literal["P0", "P1", "P2"]
    remediation_type: Literal[
        "evidence_backfill",
        "map_review",
        "time_gate_review",
        "official_id_backfill",
        "source_manifest_backfill",
    ]
    status: Literal["open"] = "open"
    source_id: str | None = None
    step_id: str | None = None
    title: str
    problem: str
    recommended_action: str
    reviewer_prompt: str
    evidence_refs: list[str] = Field(default_factory=list)
    safety_boundary: str = "Operator remediation queue only; changes require separate human review and source manifest edits."


class AchievementRouteRemediationQueue(BaseModel):
    schema_version: str = "gw2radar.achievement_route_remediation_queue.v1"
    maturity_label: Literal["blocked", "review_needed", "ready"]
    open_item_count: int
    p0_count: int
    p1_count: int
    p2_count: int
    items: list[AchievementRouteRemediationItem]
    next_actions: list[str]
    evidence_chain: list[str]
    boundary: str = "Remediation queue is a reviewer workflow aid; it does not persist source changes, enable rules, or certify live game state."


class AchievementRouteRemediationReviewRequest(BaseModel):
    item_id: str = Field(min_length=3)
    status: RouteRemediationReviewStatus
    reviewer: str = Field(min_length=2)
    notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confirmed_manual_review: bool = False


class AchievementRouteRemediationReviewRecord(BaseModel):
    schema_version: str = "gw2radar.achievement_route_remediation_review.v1"
    event_id: str
    item_id: str
    status: RouteRemediationReviewStatus
    occurred_at: datetime
    reviewer: str
    notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    source_id: str | None = None
    step_id: str | None = None
    remediation_type: str | None = None
    priority: str | None = None
    safety_boundary: str = "Remediation review audit records operator decisions only; source manifests still require separate human edits and promotion review."


class AchievementRouteRemediationReviewAuditList(BaseModel):
    schema_version: str = "gw2radar.achievement_route_remediation_review_audit_list.v1"
    records: list[AchievementRouteRemediationReviewRecord]
    filters: dict[str, str | int | None]
    boundary: str = "Remediation review audit exports are metadata-only and must not contain raw API keys or private account payloads."


class AchievementRouteRemediationReadiness(BaseModel):
    schema_version: str = "gw2radar.achievement_route_remediation_readiness.v1"
    ready: bool
    maturity_label: Literal["blocked", "review_needed", "ready"]
    readiness_score: float
    queue_item_count: int
    open_p0_count: int
    open_p1_count: int
    open_p2_count: int
    reviewed_item_count: int
    resolved_count: int
    acknowledged_count: int
    deferred_count: int
    unresolved_item_ids: list[str]
    deferred_item_ids: list[str]
    resolved_without_extra_evidence_item_ids: list[str]
    blockers: list[str]
    warnings: list[str]
    next_steps: list[str]
    evidence_chain: list[str]
    boundary: str = "Remediation readiness is an operator go/no-go gate; it does not edit source manifests or certify live game state."


class AchievementRouteOperatorActionBundleRequest(BaseModel):
    review: AchievementRouteRemediationReviewRequest | None = None


class AchievementRouteOperatorActionBundle(BaseModel):
    schema_version: str = "gw2radar.achievement_route_operator_action_bundle.v1"
    quality: AchievementRouteSourceQualityReview
    remediation_queue: AchievementRouteRemediationQueue
    remediation_review: AchievementRouteRemediationReviewRecord | None = None
    remediation_review_audit: AchievementRouteRemediationReviewAuditList
    remediation_readiness: AchievementRouteRemediationReadiness
    release_readiness: AchievementRouteReleaseReadiness
    next_actions: list[str]
    boundary: str = "Operator action bundle is a front-end workflow aggregator; it only writes remediation review audit records when an explicit confirmed review is supplied."


class AchievementRouteOperatorReleasePacket(BaseModel):
    schema_version: str = "gw2radar.achievement_route_operator_release_packet.v1"
    packet_id: str
    generated_at: datetime
    ready: bool
    maturity_label: Literal["blocked", "review_needed", "ready"]
    quality_score: float
    remediation_score: float
    release_score: float
    open_remediation_items: int
    blocker_count: int
    warning_count: int
    manifest: dict[str, Any]
    bundle: AchievementRouteOperatorActionBundle
    boundary: str = "Operator release packet is a deterministic review artifact; it does not publish, edit manifests, automate gameplay, or certify live game state."


class AchievementRouteBackfillCandidate(BaseModel):
    candidate_id: str
    item_id: str
    priority: str
    remediation_type: str
    source_id: str | None = None
    step_id: str | None = None
    title: str
    suggested_fields: dict[str, Any]
    rationale: str
    required_review: list[str]
    evidence_refs: list[str] = Field(default_factory=list)


class AchievementRouteBackfillCandidateExport(BaseModel):
    schema_version: str = "gw2radar.achievement_route_backfill_candidates.v1"
    candidate_count: int
    candidates: list[AchievementRouteBackfillCandidate]
    excluded_item_ids: list[str]
    boundary: str = "Backfill candidates are draft edit suggestions only; they do not modify source manifests or bypass reviewer promotion gates."


class AchievementRouteBackfillCandidateReviewRequest(BaseModel):
    candidate_id: str = Field(min_length=3)
    status: RouteRemediationReviewStatus
    reviewer: str = Field(min_length=2)
    notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confirmed_manual_review: bool = False


class AchievementRouteBackfillCandidateReviewRecord(BaseModel):
    schema_version: str = "gw2radar.achievement_route_backfill_candidate_review.v1"
    event_id: str
    candidate_id: str
    item_id: str
    status: RouteRemediationReviewStatus
    occurred_at: datetime
    reviewer: str
    notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    source_id: str | None = None
    step_id: str | None = None
    remediation_type: str | None = None
    priority: str | None = None
    safety_boundary: str = "Backfill candidate review records operator decisions only; source manifests still require separate manual edits and reviewed promotion."


class AchievementRouteBackfillCandidateReviewAuditList(BaseModel):
    schema_version: str = "gw2radar.achievement_route_backfill_candidate_review_audit_list.v1"
    records: list[AchievementRouteBackfillCandidateReviewRecord]
    filters: dict[str, str | int | None]
    boundary: str = "Backfill candidate audit exports are metadata-only and must not contain raw API keys or private account payloads."


class AchievementRouteBackfillCandidateReadiness(BaseModel):
    schema_version: str = "gw2radar.achievement_route_backfill_candidate_readiness.v1"
    ready: bool
    maturity_label: Literal["blocked", "review_needed", "ready"]
    readiness_score: float
    candidate_count: int
    reviewed_candidate_count: int
    resolved_count: int
    acknowledged_count: int
    deferred_count: int
    open_candidate_count: int
    unresolved_candidate_ids: list[str]
    deferred_candidate_ids: list[str]
    resolved_without_extra_evidence_candidate_ids: list[str]
    blockers: list[str]
    warnings: list[str]
    next_steps: list[str]
    evidence_chain: list[str]
    boundary: str = "Backfill readiness is an operator review gate; it does not edit source manifests, enable rules, automate gameplay, or certify live game state."


class AchievementRouteSourceEditPatchOperation(BaseModel):
    operation_id: str
    candidate_id: str
    operation_type: Literal["add", "replace", "review"]
    target_type: Literal["source_manifest", "route_step"]
    source_id: str | None = None
    step_id: str | None = None
    field_path: str
    current_value: Any | None = None
    proposed_value: Any
    rationale: str
    evidence_refs: list[str] = Field(default_factory=list)
    required_review: list[str] = Field(default_factory=list)


class AchievementRouteSourceEditPatchDraft(BaseModel):
    draft_id: str
    candidate_id: str
    item_id: str
    priority: str
    remediation_type: str
    title: str
    reviewer: str
    reviewed_at: datetime
    source_id: str | None = None
    step_id: str | None = None
    source_manifest_path: str | None = None
    operations: list[AchievementRouteSourceEditPatchOperation]
    evidence_refs: list[str] = Field(default_factory=list)
    safety_boundary: str = "Patch draft is an operator review artifact only; it does not modify source manifests or promote reviewed guidance."


class AchievementRouteSourceEditPatchDraftExport(BaseModel):
    schema_version: str = "gw2radar.achievement_route_source_edit_patch_draft.v1"
    generated_at: datetime
    draft_count: int
    operation_count: int
    drafts: list[AchievementRouteSourceEditPatchDraft]
    excluded_candidate_ids: list[str]
    blockers: list[str]
    warnings: list[str]
    next_steps: list[str]
    evidence_chain: list[str]
    boundary: str = "Source edit patch drafts are deterministic review artifacts; operators must apply, review, and promote source manifests separately."


class AchievementRouteSourceEditPatchApplyRequest(BaseModel):
    draft_id: str = Field(min_length=3)
    reviewer: str = Field(min_length=2)
    notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    output_source_id: str | None = None
    confirmed_manual_review: bool = False


class AchievementRouteSourceEditPatchApplyRecord(BaseModel):
    schema_version: str = "gw2radar.achievement_route_source_edit_patch_apply.v1"
    event_id: str
    draft_id: str
    candidate_id: str
    source_id: str | None = None
    output_source_id: str
    output_manifest_path: str
    operation_count: int
    applied_at: datetime
    reviewer: str
    notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    safety_boundary: str = "Patch apply writes a draft source manifest only; reviewed ingestion still requires separate promotion and release readiness review."


class AchievementRouteSourceEditPatchApplyAuditList(BaseModel):
    schema_version: str = "gw2radar.achievement_route_source_edit_patch_apply_audit_list.v1"
    records: list[AchievementRouteSourceEditPatchApplyRecord]
    filters: dict[str, str | int | None]
    boundary: str = "Patch apply audit exports are metadata-only and must not contain raw API keys or private account payloads."


class AchievementRouteDraftSourcePromotionRequest(BaseModel):
    draft_source_id: str = Field(min_length=3)
    reviewer: str = Field(min_length=2)
    reviewed_source_id: str | None = None
    review_notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    overwrite_existing: bool = False
    confirmed_reviewed: bool = False


class AchievementRouteDraftSourcePromotionRecord(BaseModel):
    schema_version: str = "gw2radar.achievement_route_draft_source_promotion.v1"
    event_id: str
    draft_source_id: str
    reviewed_source_id: str
    reviewer: str
    promoted_at: datetime
    manifest_path: str
    step_count: int
    review_notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    planner_ingestion_status: Literal["ready", "blocked"]
    safety_boundary: str = "Draft source promotion requires human review; reviewed manifest ingestion remains visible through release readiness."


class AchievementRouteDraftSourcePromotionAuditList(BaseModel):
    schema_version: str = "gw2radar.achievement_route_draft_source_promotion_audit_list.v1"
    records: list[AchievementRouteDraftSourcePromotionRecord]
    filters: dict[str, str | int | None]
    boundary: str = "Draft source promotion audit exports are metadata-only and must not contain raw API keys or private account payloads."


class AchievementRouteUnifiedReleaseEvidenceBundle(BaseModel):
    schema_version: str = "gw2radar.achievement_route_unified_release_evidence_bundle.v1"
    bundle_id: str
    generated_at: datetime
    ready: bool
    maturity_label: Literal["blocked", "review_needed", "ready"]
    reviewed_source_count: int
    reviewed_step_count: int
    official_promotion_audit_count: int
    patch_apply_audit_count: int
    draft_source_promotion_audit_count: int
    quality_score: float
    release_score: float
    remediation_score: float
    blocker_count: int
    warning_count: int
    source_ids: list[str]
    artifacts: list[str]
    evidence_chain: list[str]
    manifest: dict[str, Any]
    release_readiness: AchievementRouteReleaseReadiness
    quality: AchievementRouteSourceQualityReview
    operator_release_packet: AchievementRouteOperatorReleasePacket
    official_promotion_audit: AchievementRoutePromotionAuditList
    source_patch_apply_audit: AchievementRouteSourceEditPatchApplyAuditList
    draft_source_promotion_audit: AchievementRouteDraftSourcePromotionAuditList
    boundary: str = "Unified release evidence bundle is a read-only handoff artifact; it does not publish, edit manifests, automate gameplay, or certify live game state."


class AchievementRouteReleaseEvidenceArchiveRecord(BaseModel):
    schema_version: str = "gw2radar.achievement_route_release_evidence_archive_record.v1"
    archive_id: str
    bundle_id: str
    archived_at: datetime
    generated_at: datetime
    archived_by: str
    checksum_sha256: str
    retention_policy: str
    ready: bool
    maturity_label: Literal["blocked", "review_needed", "ready"]
    reviewed_source_count: int
    reviewed_step_count: int
    blocker_count: int
    warning_count: int
    source_ids: list[str]
    artifacts: list[str]
    evidence_chain: list[str]
    manifest_schema: str
    source_bundle_schema: str
    safety_boundary: str = "Release evidence archives are immutable metadata snapshots; they do not publish content, edit source manifests, automate gameplay, or store secrets."


class AchievementRouteReleaseEvidenceArchiveIndex(BaseModel):
    schema_version: str = "gw2radar.achievement_route_release_evidence_archive_index.v1"
    records: list[AchievementRouteReleaseEvidenceArchiveRecord]
    filters: dict[str, str | int | None]
    total_records: int
    latest_archive_id: str | None = None
    boundary: str = "Archive index exports are metadata-only and must not include raw API keys or private account payloads."


class AchievementRouteReleaseEvidenceArchiveDiff(BaseModel):
    schema_version: str = "gw2radar.achievement_route_release_evidence_archive_diff.v1"
    generated_at: datetime
    baseline_archive_id: str | None = None
    candidate_archive_id: str | None = None
    ready: bool
    maturity_label: Literal["blocked", "review_needed", "ready"]
    regression_count: int
    improvement_count: int
    unchanged_count: int
    source_added: list[str] = Field(default_factory=list)
    source_removed: list[str] = Field(default_factory=list)
    artifact_added: list[str] = Field(default_factory=list)
    artifact_removed: list[str] = Field(default_factory=list)
    evidence_chain_added: list[str] = Field(default_factory=list)
    evidence_chain_removed: list[str] = Field(default_factory=list)
    metric_deltas: dict[str, int] = Field(default_factory=dict)
    checksum_changed: bool = False
    maturity_changed: bool = False
    blocker_delta: int = 0
    warning_delta: int = 0
    reviewed_source_delta: int = 0
    reviewed_step_delta: int = 0
    findings: list[str] = Field(default_factory=list)
    regressions: list[str] = Field(default_factory=list)
    improvements: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    boundary: str = "Release evidence archive diff is metadata-only; it does not publish, edit source manifests, certify live game state, or inspect private account payloads."


class AchievementRouteReleaseSignoffRequest(BaseModel):
    reviewer: str = Field(min_length=2)
    notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    confirmed_signoff: bool = False


class AchievementRouteReleaseSignoffRecord(BaseModel):
    schema_version: str = "gw2radar.achievement_route_release_signoff.v1"
    signoff_id: str
    signed_off_at: datetime
    reviewer: str
    status: Literal["signed_off", "blocked"]
    bundle_id: str
    archive_id: str | None = None
    diff_baseline_archive_id: str | None = None
    diff_candidate_archive_id: str | None = None
    bundle_maturity: str
    archive_maturity: str | None = None
    diff_maturity: str
    regression_count: int
    blocker_count: int
    warning_count: int
    checksum_changed: bool
    notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    safety_boundary: str = "Release sign-off is metadata-only; it records reviewer confirmation and does not publish content, edit source manifests, automate gameplay, or store secrets."


class AchievementRouteReleaseSignoffAuditList(BaseModel):
    schema_version: str = "gw2radar.achievement_route_release_signoff_audit_list.v1"
    records: list[AchievementRouteReleaseSignoffRecord]
    filters: dict[str, str | int | None]
    boundary: str = "Release sign-off audit exports are metadata-only and must not contain raw API keys or private account payloads."


class AchievementRouteOperatorReleaseDashboard(BaseModel):
    schema_version: str = "gw2radar.achievement_route_operator_release_dashboard.v1"
    generated_at: datetime
    ready: bool
    maturity_label: Literal["blocked", "review_needed", "ready"]
    bundle_id: str
    bundle_maturity: str
    archive_count: int
    latest_archive_id: str | None = None
    diff_maturity: str
    diff_regression_count: int
    latest_signoff_id: str | None = None
    latest_signoff_status: str | None = None
    latest_signoff_reviewer: str | None = None
    missing_gates: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    release_evidence_bundle: AchievementRouteUnifiedReleaseEvidenceBundle
    release_evidence_archive_index: AchievementRouteReleaseEvidenceArchiveIndex
    release_evidence_archive_diff: AchievementRouteReleaseEvidenceArchiveDiff
    release_signoff_audit: AchievementRouteReleaseSignoffAuditList
    boundary: str = "Operator release dashboard is a read-only metadata summary; it does not publish content, edit source manifests, automate gameplay, or store secrets."


class AchievementRouteReleaseExportPacket(BaseModel):
    schema_version: str = "gw2radar.achievement_route_release_export_packet.v1"
    packet_id: str
    generated_at: datetime
    ready: bool
    maturity_label: Literal["blocked", "review_needed", "ready"]
    dashboard_schema: str
    bundle_schema: str
    archive_index_schema: str
    diff_schema: str
    signoff_audit_schema: str
    bundle_id: str
    latest_archive_id: str | None = None
    diff_baseline_archive_id: str | None = None
    diff_candidate_archive_id: str | None = None
    latest_signoff_id: str | None = None
    latest_signoff_status: str | None = None
    artifact_count: int
    artifacts: list[str]
    evidence_refs: list[str]
    manifest: dict[str, Any]
    dashboard: AchievementRouteOperatorReleaseDashboard
    boundary: str = "Release export packet is a metadata-only final handoff artifact; it does not publish content, edit source manifests, automate gameplay, store secrets, or certify live game state."


class AchievementRouteReleaseExportArtifactFile(BaseModel):
    filename: str
    relative_path: str
    media_type: str
    size_bytes: int
    checksum_sha256: str


class AchievementRouteReleaseExportArtifactIndex(BaseModel):
    schema_version: str = "gw2radar.achievement_route_release_export_artifact_index.v1"
    packet_id: str | None = None
    packet_dir: str | None = None
    generated_at: datetime
    file_count: int
    files: list[AchievementRouteReleaseExportArtifactFile]
    boundary: str = "Release export artifact index is local metadata only; it does not publish files externally or include secrets."


class AchievementRouteReleaseExportBundleManifest(BaseModel):
    schema_version: str = "gw2radar.achievement_route_release_export_bundle_manifest.v1"
    bundle_id: str
    packet_id: str | None = None
    generated_at: datetime
    filename: str
    media_type: str = "application/zip"
    file_count: int
    included_files: list[AchievementRouteReleaseExportArtifactFile]
    checksum_sha256: str
    size_bytes: int
    boundary: str = "Release export bundle is a local read-only zip package; it does not publish files externally, include secrets, or certify live game state."


class AchievementRouteReleaseExportBundleVerification(BaseModel):
    schema_version: str = "gw2radar.achievement_route_release_export_bundle_verification.v1"
    ready: bool
    verified_at: datetime
    checksum_sha256: str
    size_bytes: int
    file_count: int
    verified_files: list[str]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    boundary: str = "Release export bundle verification reads local zip bytes only; it does not execute files, publish content, store secrets, or certify live game state."


class AchievementRouteReleaseExportBundleVerificationAuditRequest(BaseModel):
    reviewer: str = Field(min_length=2)
    notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    expected_checksum_sha256: str | None = None


class AchievementRouteReleaseExportBundleVerificationAuditRecord(BaseModel):
    schema_version: str = "gw2radar.achievement_route_release_export_bundle_verification_audit.v1"
    audit_id: str
    verified_at: datetime
    reviewer: str
    ready: bool
    checksum_sha256: str
    size_bytes: int
    file_count: int
    blocker_count: int
    warning_count: int
    verified_files: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    safety_boundary: str = "Release bundle verification audit is metadata-only; it records validation results and does not store zip bytes, publish files, execute uploads, or store secrets."


class AchievementRouteReleaseExportBundleVerificationAuditList(BaseModel):
    schema_version: str = "gw2radar.achievement_route_release_export_bundle_verification_audit_list.v1"
    records: list[AchievementRouteReleaseExportBundleVerificationAuditRecord]
    filters: dict[str, str | int | bool | None]
    boundary: str = "Release bundle verification audit exports are metadata-only and must not include zip content, raw API keys, or private account payloads."


class AchievementRouteOperatorHandoffChecklist(BaseModel):
    schema_version: str = "gw2radar.achievement_route_operator_handoff_checklist.v1"
    generated_at: datetime
    ready: bool
    maturity_label: Literal["blocked", "review_needed", "ready"]
    packet_id: str | None = None
    packet_artifact_count: int
    bundle_checksum_sha256: str | None = None
    bundle_file_count: int
    verification_ready: bool
    verification_audit_count: int
    latest_verification_audit_id: str | None = None
    checklist_items: list[str] = Field(default_factory=list)
    missing_gates: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    boundary: str = "Operator handoff checklist is metadata-only; it does not publish files, execute bundle content, certify live game state, or store secrets."


class AchievementRouteGateway(Protocol):
    def get_batch(
        self,
        endpoint: str,
        *,
        ids: list[int | str],
        params: dict[str, Any] | None = None,
        api_key: str | None = None,
        priority: str = "P3",
    ):
        ...


SAMPLE_ROUTE_STEPS: tuple[AchievementRouteStep, ...] = (
    AchievementRouteStep(
        step_id="aurora-bloodstone-fen-check",
        title="Bloodstone Fen collection sweep",
        step_type="collection",
        map_name="Bloodstone Fen",
        region="Maguuma Wastes",
        objective="Check unlocked local collection progress and finish one visible map-bound objective.",
        advances_goal_id="aurora_sample",
        prerequisite_ids=["living_world_s3_access"],
        estimated_minutes=15,
        evidence_refs=["kb:seed:legendary-route:v1"],
        assumptions=["Sample route seed; verify the exact in-game achievement panel before execution."],
        source_id="kb:seed:legendary-route:v1",
    ),
    AchievementRouteStep(
        step_id="aurora-ember-bay-daily-token",
        title="Ember Bay daily token pass",
        step_type="collection",
        map_name="Ember Bay",
        region="Ring of Fire",
        objective="Do one short account-progress pass tied to the active legendary collection.",
        advances_goal_id="aurora_sample",
        prerequisite_ids=["living_world_s3_access"],
        time_gate="daily",
        estimated_minutes=12,
        evidence_refs=["kb:seed:legendary-route:v1"],
        assumptions=["Daily availability is represented as a planning gate, not a guarantee of current rotation."],
        source_id="kb:seed:legendary-route:v1",
    ),
    AchievementRouteStep(
        step_id="vision-dragonfall-meta",
        title="Dragonfall group event checkpoint",
        step_type="achievement",
        map_name="Dragonfall",
        region="Crystal Desert",
        objective="Reserve time for a group/meta checkpoint if the account is also advancing Vision-like goals.",
        advances_goal_id="vision_sample",
        prerequisite_ids=["living_world_s4_access"],
        time_gate="weekly",
        estimated_minutes=25,
        group_required=True,
        evidence_refs=["kb:seed:legendary-route:v1"],
        assumptions=["Group event timing must be confirmed in game or with the squad before committing the session."],
        source_id="kb:seed:legendary-route:v1",
    ),
    AchievementRouteStep(
        step_id="fractals-ad-infinitum-check",
        title="Fractal collection checkpoint",
        step_type="achievement",
        map_name="Fractals of the Mists",
        region="Mistlock Observatory",
        objective="Check one fractal collection blocker and defer if group or tier access is missing.",
        advances_goal_id="ad_infinitum_sample",
        prerequisite_ids=["fractal_access"],
        estimated_minutes=20,
        group_required=True,
        evidence_refs=["kb:seed:legendary-route:v1"],
        assumptions=["Fractal tier, instability, and group readiness are player-provided facts until synced or entered."],
        source_id="kb:seed:legendary-route:v1",
    ),
)


def build_achievement_route_plan(
    request: AchievementRouteRequest,
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
) -> AchievementRoutePlan:
    source_steps, source_summaries = load_reviewed_achievement_route_steps(source_root)
    route_steps = source_steps or list(SAMPLE_ROUTE_STEPS)
    source_warnings = [
        summary.warning for summary in source_summaries if summary.warning
    ]
    if not source_steps:
        source_warnings.append("No reviewed achievement route source manifests were loaded; using built-in MVP fallback seed.")

    completed = set(request.completed_step_ids)
    unlocked = set(request.unlocked_prerequisite_ids)
    candidate_steps = [
        step
        for step in route_steps
        if step.step_id not in completed and (request.goal_id == "all" or step.advances_goal_id == request.goal_id)
    ]
    if not candidate_steps:
        candidate_steps = [step for step in route_steps if step.step_id not in completed]

    ready: list[str] = []
    blocked: list[str] = []
    time_gated: list[str] = []
    for step in candidate_steps:
        missing_prereqs = [prereq for prereq in step.prerequisite_ids if prereq not in unlocked]
        if missing_prereqs or (step.group_required and not request.include_group_content):
            blocked.append(step.step_id)
            continue
        if step.time_gate != "none":
            time_gated.append(step.step_id)
        ready.append(step.step_id)

    segments = _build_segments(candidate_steps, ready, blocked, time_gated)
    limited_ready = _fit_ready_steps(candidate_steps, ready, request.available_minutes)
    actions = _build_actions(candidate_steps, segments, limited_ready, blocked, time_gated, request.available_minutes)
    return AchievementRoutePlan(
        route_id=f"route:{request.user_id}:{request.goal_id}",
        user_id=request.user_id,
        goal_id=request.goal_id,
        generated_at=datetime.now(UTC),
        available_minutes=request.available_minutes,
        steps=candidate_steps,
        segments=segments,
        ready_step_ids=limited_ready,
        blocked_step_ids=blocked,
        time_gated_step_ids=time_gated,
        next_actions=actions,
        source_ids=_unique([step.source_id for step in candidate_steps]),
        source_warnings=_unique(source_warnings),
        assumptions=_unique(
            [
                "This MVP planner uses reviewed KB route source manifests plus player-provided prerequisite state.",
                "Exact achievement step completion must be checked in the in-game achievement panel.",
                *[assumption for step in candidate_steps for assumption in step.assumptions],
            ]
        ),
        safety_boundaries=[
            "Manual planning only; GW2Radar does not automate gameplay, squad joining, trading, or collection completion.",
            "Routes are advisory and must be verified against current account state and current patch context.",
        ],
    )


def render_achievement_route_markdown(plan: AchievementRoutePlan) -> str:
    step_by_id = {step.step_id: step for step in plan.steps}
    lines = [
        "# Achievement & Collection Route Plan",
        "",
        f"- User: {plan.user_id}",
        f"- Goal: {plan.goal_id}",
        f"- Available minutes: {plan.available_minutes}",
        f"- Ready steps: {len(plan.ready_step_ids)}",
        f"- Blocked steps: {len(plan.blocked_step_ids)}",
        f"- Sources: {', '.join(plan.source_ids) if plan.source_ids else 'none'}",
        "",
        "## Route Segments",
    ]
    for segment in plan.segments:
        lines.extend(
            [
                f"### {segment.map_name}",
                f"- Region: {segment.region}",
                f"- Ready minutes: {segment.total_ready_minutes}",
                f"- Ready: {_step_titles(step_by_id, segment.ready_step_ids) or 'none'}",
                f"- Blocked: {_step_titles(step_by_id, segment.blocked_step_ids) or 'none'}",
                f"- Time gated: {_step_titles(step_by_id, segment.time_gated_step_ids) or 'none'}",
            ]
        )
        lines.extend([f"- Note: {note}" for note in segment.notes])
        lines.append("")
    lines.extend(["## Next Actions"])
    lines.extend([f"- {action.title}: {action.reason}" for action in plan.next_actions] or ["- No route actions available."])
    lines.extend(["", "## Source Warnings"])
    lines.extend([f"- {warning}" for warning in plan.source_warnings] or ["- None"])
    lines.extend(["", "## Assumptions"])
    lines.extend([f"- {assumption}" for assumption in plan.assumptions])
    lines.extend(["", "## Safety Boundaries"])
    lines.extend([f"- {boundary}" for boundary in plan.safety_boundaries])
    return "\n".join(lines) + "\n"


def render_achievement_route_csv(plan: AchievementRoutePlan) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "step_id",
            "title",
            "map_name",
            "region",
            "status",
            "time_gate",
            "estimated_minutes",
            "objective",
            "evidence_refs",
            "source_id",
        ]
    )
    for step in plan.steps:
        status = "ready"
        if step.step_id in plan.blocked_step_ids:
            status = "blocked"
        elif step.step_id in plan.time_gated_step_ids:
            status = "time_gated"
        writer.writerow(
            [
                step.step_id,
                step.title,
                step.map_name,
                step.region,
                status,
                step.time_gate,
                step.estimated_minutes,
                step.objective,
                ";".join(step.evidence_refs),
                step.source_id,
            ]
        )
    return buffer.getvalue()


def load_reviewed_achievement_route_steps(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
) -> tuple[list[AchievementRouteStep], list[AchievementRouteSourceSummary]]:
    manifests = load_achievement_route_source_manifests(source_root)
    reviewed_steps: list[AchievementRouteStep] = []
    summaries: list[AchievementRouteSourceSummary] = []
    for manifest in manifests:
        if isinstance(manifest, AchievementRouteSourceSummary):
            summaries.append(manifest)
            continue
        if manifest.source_status != "reviewed":
            summaries.append(
                AchievementRouteSourceSummary(
                    source_id=manifest.source_id,
                    title=manifest.title,
                    source_status=manifest.source_status,
                    source_url=manifest.source_url,
                    source_refs=manifest.source_refs,
                    reviewed_by=manifest.reviewed_by,
                    reviewed_at=manifest.reviewed_at,
                    step_count=0,
                    warning=f"{manifest.source_id} skipped because status is {manifest.source_status}.",
                )
            )
            continue
        steps = [
            step.model_copy(
                update={
                    "source_id": manifest.source_id,
                    "source_status": manifest.source_status,
                    "evidence_refs": _unique([*step.evidence_refs, *manifest.source_refs, manifest.source_id]),
                    "assumptions": _unique([*manifest.assumptions, *step.assumptions]),
                }
            )
            for step in manifest.steps
        ]
        reviewed_steps.extend(steps)
        summaries.append(
            AchievementRouteSourceSummary(
                source_id=manifest.source_id,
                title=manifest.title,
                source_status=manifest.source_status,
                source_url=manifest.source_url,
                source_refs=manifest.source_refs,
                reviewed_by=manifest.reviewed_by,
                reviewed_at=manifest.reviewed_at,
                step_count=len(steps),
            )
        )
    return reviewed_steps, summaries


def load_achievement_route_source_manifests(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
) -> list[AchievementRouteSourceManifest | AchievementRouteSourceSummary]:
    if not source_root.exists():
        return [
            AchievementRouteSourceSummary(
                source_id="missing:achievement-route-source-root",
                title="Achievement route source root",
                source_status="disabled",
                warning=f"Source root not found: {source_root.as_posix()}",
            )
        ]
    manifests: list[AchievementRouteSourceManifest | AchievementRouteSourceSummary] = []
    for path in sorted(source_root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            manifest = AchievementRouteSourceManifest.model_validate(payload)
        except (OSError, json.JSONDecodeError, ValidationError) as exc:
            manifests.append(
                AchievementRouteSourceSummary(
                    source_id=f"invalid:{path.name}",
                    title=path.name,
                    source_status="disabled",
                    warning=f"{path.as_posix()} could not be loaded: {exc}",
                )
            )
            continue
        manifests.append(manifest)
    if not manifests:
        manifests.append(
            AchievementRouteSourceSummary(
                source_id="empty:achievement-route-source-root",
                title="Achievement route source root",
                source_status="disabled",
                warning=f"No route manifest JSON files found in {source_root.as_posix()}",
            )
        )
    return manifests


def build_official_achievement_route_preview(
    request: OfficialAchievementRoutePreviewRequest,
) -> OfficialAchievementRoutePreview:
    progress_by_id = {item.id: item for item in request.account_achievements}
    steps: list[AchievementRouteStep] = []
    warnings = [
        "Generated preview is draft-only. Save it as a reviewed source manifest only after human verification.",
        "Official achievement details do not always contain map or route order; inferred map fields must be reviewed.",
    ]
    for detail in sorted(request.achievement_details, key=lambda item: (item.name.lower(), item.id)):
        progress = progress_by_id.get(detail.id)
        progress_status, progress_note = _official_progress_status(progress)
        map_name, region, map_assumption = _infer_official_route_location(detail)
        time_gate = _infer_official_time_gate(detail)
        group_required = _infer_official_group_required(detail)
        step_id = f"official-achievement-{detail.id}"
        objective = _official_objective(detail)
        assumptions = _unique(
            [
                "Official achievement detail imported as a draft route candidate, not reviewed guidance.",
                map_assumption,
                "Route order, waypoint choice, and collection substeps require human review.",
            ]
        )
        steps.append(
            AchievementRouteStep(
                step_id=step_id,
                title=detail.name,
                step_type="achievement",
                map_name=map_name,
                region=region,
                objective=objective,
                advances_goal_id=request.goal_id,
                prerequisite_ids=["achievement_api_access"],
                time_gate=time_gate,
                estimated_minutes=_estimate_official_minutes(detail, group_required),
                group_required=group_required,
                evidence_refs=_unique([*request.source_refs, f"official:/v2/achievements/{detail.id}"]),
                assumptions=assumptions,
                source_id=request.source_id,
                source_status="draft",
                official_achievement_id=detail.id,
                account_progress_status=progress_status,
                account_progress_note=progress_note,
            )
        )
    manifest = AchievementRouteSourceManifest(
        source_id=request.source_id,
        title=request.title,
        source_status="draft",
        source_url="official:/v2/achievements",
        source_refs=request.source_refs,
        reviewed_by=request.reviewed_by,
        reviewed_at=datetime.now(UTC).date().isoformat(),
        assumptions=[
            "This draft source was generated from official achievement/account-achievement payloads.",
            "Human review is required before changing source_status to reviewed.",
            "No raw API key or private account payload is stored in this manifest.",
        ],
        steps=steps,
    )
    summary = AchievementRouteSourceSummary(
        source_id=manifest.source_id,
        title=manifest.title,
        source_status=manifest.source_status,
        source_url=manifest.source_url,
        source_refs=manifest.source_refs,
        reviewed_by=manifest.reviewed_by,
        reviewed_at=manifest.reviewed_at,
        step_count=len(steps),
        warning="Draft official preview requires human review before route planner ingestion.",
    )
    return OfficialAchievementRoutePreview(
        manifest=manifest,
        source_summary=summary,
        candidate_step_count=len(steps),
        completed_step_ids=[step.step_id for step in steps if step.account_progress_status == "complete"],
        warnings=warnings,
    )


def build_official_achievement_fetch_preview(
    request: OfficialAchievementFetchPreviewRequest,
    gateway: AchievementRouteGateway,
    *,
    account_achievements: list[OfficialAccountAchievementProgress] | None = None,
    extra_warnings: list[str] | None = None,
) -> OfficialAchievementFetchPreview:
    details_result = gateway.get_batch("/v2/achievements", ids=request.achievement_ids, priority="P2")
    detail_status = _gateway_status_value(details_result)
    warnings = list(extra_warnings or [])
    details_payload = getattr(details_result, "payload", None)
    achievement_details = _official_details_from_payload(details_payload)
    fetched_ids = sorted({detail.id for detail in achievement_details})
    missing_ids = [achievement_id for achievement_id in request.achievement_ids if achievement_id not in fetched_ids]
    if detail_status not in {"ok", "cache_hit"}:
        warnings.append(f"Official achievement detail fetch returned status {detail_status}.")
    if missing_ids:
        warnings.append(f"Official achievement detail payload did not include ids: {', '.join(map(str, missing_ids))}.")
    progress = account_achievements if account_achievements is not None else request.account_achievements
    if not progress:
        warnings.append("No account achievement progress was available; candidate progress statuses remain unknown.")
    preview_request = OfficialAchievementRoutePreviewRequest(
        source_id=request.source_id,
        title=request.title,
        goal_id=request.goal_id,
        reviewed_by=request.reviewed_by,
        achievement_details=achievement_details,
        account_achievements=progress,
        source_refs=[
            "official:/v2/achievements?ids=" + ",".join(str(item) for item in request.achievement_ids),
            "official:/v2/account/achievements",
        ],
    )
    preview = build_official_achievement_route_preview(preview_request)
    return OfficialAchievementFetchPreview(
        preview=preview,
        requested_achievement_ids=request.achievement_ids,
        fetched_achievement_ids=fetched_ids,
        missing_achievement_ids=missing_ids,
        gateway_statuses={"/v2/achievements": detail_status},
        warnings=_unique([*warnings, *preview.warnings]),
    )


def render_official_achievement_route_preview_markdown(preview: OfficialAchievementRoutePreview) -> str:
    lines = [
        "# Official Achievement Route Preview",
        "",
        f"- Source: {preview.manifest.source_id}",
        f"- Status: {preview.manifest.source_status}",
        f"- Candidate steps: {preview.candidate_step_count}",
        f"- Completed from account progress: {len(preview.completed_step_ids)}",
        "",
        "## Candidate Steps",
    ]
    for step in preview.manifest.steps:
        lines.extend(
            [
                f"- {step.title}",
                f"  - Achievement id: {step.official_achievement_id}",
                f"  - Map: {step.map_name}",
                f"  - Progress: {step.account_progress_status} ({step.account_progress_note or 'no account progress supplied'})",
                f"  - Evidence: {', '.join(step.evidence_refs)}",
            ]
        )
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {warning}" for warning in preview.warnings])
    lines.extend(["", "## Assumptions"])
    lines.extend([f"- {assumption}" for assumption in preview.manifest.assumptions])
    return "\n".join(lines) + "\n"


def render_official_achievement_fetch_preview_markdown(fetch_preview: OfficialAchievementFetchPreview) -> str:
    lines = [
        "# Official Achievement Fetch Preview",
        "",
        f"- Requested ids: {', '.join(map(str, fetch_preview.requested_achievement_ids))}",
        f"- Fetched ids: {', '.join(map(str, fetch_preview.fetched_achievement_ids)) or 'none'}",
        f"- Missing ids: {', '.join(map(str, fetch_preview.missing_achievement_ids)) or 'none'}",
        f"- Achievement gateway status: {fetch_preview.gateway_statuses.get('/v2/achievements', 'unknown')}",
        "",
        "## Draft Route Preview",
        render_official_achievement_route_preview_markdown(fetch_preview.preview).strip(),
        "",
        "## Fetch Warnings",
    ]
    lines.extend([f"- {warning}" for warning in fetch_preview.warnings] or ["- None"])
    return "\n".join(lines) + "\n"


def promote_official_fetch_preview_to_reviewed_manifest(
    fetch_preview: OfficialAchievementFetchPreview,
    request: AchievementRouteReviewedPromotionRequest,
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
) -> AchievementRouteReviewedPromotionResult:
    if not request.confirmed_reviewed:
        raise ValueError("Promoting an official achievement fetch preview requires reviewed confirmation.")
    if not fetch_preview.preview.manifest.steps:
        raise ValueError("Cannot promote an official achievement fetch preview with no candidate steps.")

    reviewed_source_id = request.reviewed_source_id or _reviewed_source_id(fetch_preview.preview.manifest.source_id)
    manifest_path = _reviewed_manifest_path(source_root, reviewed_source_id)
    if manifest_path.exists() and not request.overwrite_existing:
        raise FileExistsError(f"Reviewed achievement route manifest already exists: {manifest_path.as_posix()}")

    review_notes = request.review_notes or ["Human reviewer confirmed this official fetch preview for planner ingestion."]
    manifest = fetch_preview.preview.manifest.model_copy(
        update={
            "source_id": reviewed_source_id,
            "source_status": "reviewed",
            "reviewed_by": request.reviewer,
            "reviewed_at": datetime.now(UTC).date().isoformat(),
            "assumptions": _unique(
                [
                    *fetch_preview.preview.manifest.assumptions,
                    "This manifest was promoted from an official fetch preview through the reviewed gate.",
                    *review_notes,
                    *fetch_preview.warnings,
                ]
            ),
            "steps": [
                step.model_copy(
                    update={
                        "source_id": reviewed_source_id,
                        "source_status": "reviewed",
                        "evidence_refs": _unique([*step.evidence_refs, reviewed_source_id]),
                        "assumptions": _unique(
                            [
                                *step.assumptions,
                                "Human reviewer promoted this official achievement candidate for route planning.",
                            ]
                        ),
                    }
                )
                for step in fetch_preview.preview.manifest.steps
            ],
        }
    )
    source_root.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )
    summary = AchievementRouteSourceSummary(
        source_id=manifest.source_id,
        title=manifest.title,
        source_status=manifest.source_status,
        source_url=manifest.source_url,
        source_refs=manifest.source_refs,
        reviewed_by=manifest.reviewed_by,
        reviewed_at=manifest.reviewed_at,
        step_count=len(manifest.steps),
    )
    warnings = _unique(
        [
            "Reviewed manifest is now eligible for route planner ingestion.",
            *fetch_preview.warnings,
        ]
    )
    return AchievementRouteReviewedPromotionResult(
        manifest=manifest,
        manifest_path=manifest_path.as_posix(),
        source_summary=summary,
        planner_ingestion_status="ready",
        warnings=warnings,
    )


def record_achievement_route_promotion_audit(
    promotion: AchievementRouteReviewedPromotionResult,
    fetch_preview: OfficialAchievementFetchPreview,
    review: AchievementRouteReviewedPromotionRequest,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRoutePromotionAuditRecord:
    occurred_at = datetime.now(UTC)
    record = AchievementRoutePromotionAuditRecord(
        event_id=f"achievement-route-promotion:{occurred_at.strftime('%Y%m%dT%H%M%S%fZ')}:{_safe_identifier(promotion.manifest.source_id)}",
        action="promote_reviewed",
        occurred_at=occurred_at,
        reviewer=review.reviewer,
        source_id=promotion.manifest.source_id,
        source_status=promotion.manifest.source_status,
        manifest_path=promotion.manifest_path,
        requested_achievement_ids=fetch_preview.requested_achievement_ids,
        fetched_achievement_ids=fetch_preview.fetched_achievement_ids,
        missing_achievement_ids=fetch_preview.missing_achievement_ids,
        candidate_step_count=len(promotion.manifest.steps),
        review_notes=review.review_notes or ["Human reviewer confirmed this official fetch preview for planner ingestion."],
        evidence_refs=_unique(
            [
                *promotion.manifest.source_refs,
                *[ref for step in promotion.manifest.steps for ref in step.evidence_refs],
                promotion.manifest.source_id,
            ]
        ),
        planner_ingestion_status=promotion.planner_ingestion_status,
    )
    audit_root.mkdir(parents=True, exist_ok=True)
    path = audit_root / "promotion_audit.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(record.model_dump_json() + "\n")
    return record


def list_achievement_route_promotion_audits(
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    *,
    reviewer: str | None = None,
    source_id: str | None = None,
    limit: int = 25,
) -> AchievementRoutePromotionAuditList:
    path = audit_root / "promotion_audit.jsonl"
    records: list[AchievementRoutePromotionAuditRecord] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = AchievementRoutePromotionAuditRecord.model_validate_json(line)
            except ValidationError:
                continue
            if reviewer and record.reviewer != reviewer:
                continue
            if source_id and record.source_id != source_id:
                continue
            records.append(record)
    records = sorted(records, key=lambda item: item.occurred_at, reverse=True)[: max(1, min(limit, 200))]
    return AchievementRoutePromotionAuditList(
        records=records,
        filters={"reviewer": reviewer, "source_id": source_id, "limit": limit},
    )


def render_achievement_route_promotion_audit_markdown(audit_list: AchievementRoutePromotionAuditList) -> str:
    lines = [
        "# Achievement Route Promotion Audit",
        "",
        f"- Records: {len(audit_list.records)}",
        f"- Boundary: {audit_list.boundary}",
        "",
        "| Occurred At | Reviewer | Source | Status | Steps | Missing IDs | Manifest |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for record in audit_list.records:
        lines.append(
            "| "
            + " | ".join(
                [
                    record.occurred_at.isoformat(),
                    record.reviewer,
                    record.source_id,
                    record.planner_ingestion_status,
                    str(record.candidate_step_count),
                    ",".join(map(str, record.missing_achievement_ids)) or "none",
                    record.manifest_path,
                ]
            )
            + " |"
        )
    if not audit_list.records:
        lines.append("| none | none | none | none | 0 | none | none |")
    return "\n".join(lines) + "\n"


def render_achievement_route_promotion_audit_csv(audit_list: AchievementRoutePromotionAuditList) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "event_id",
            "occurred_at",
            "reviewer",
            "source_id",
            "planner_ingestion_status",
            "candidate_step_count",
            "requested_achievement_ids",
            "fetched_achievement_ids",
            "missing_achievement_ids",
            "manifest_path",
        ]
    )
    for record in audit_list.records:
        writer.writerow(
            [
                record.event_id,
                record.occurred_at.isoformat(),
                record.reviewer,
                record.source_id,
                record.planner_ingestion_status,
                record.candidate_step_count,
                ";".join(map(str, record.requested_achievement_ids)),
                ";".join(map(str, record.fetched_achievement_ids)),
                ";".join(map(str, record.missing_achievement_ids)),
                record.manifest_path,
            ]
        )
    return buffer.getvalue()


def build_achievement_route_release_readiness(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteReleaseReadiness:
    reviewed_steps, summaries = load_reviewed_achievement_route_steps(source_root)
    audit_list = list_achievement_route_promotion_audits(audit_root, limit=200)
    reviewed_sources = [
        summary for summary in summaries if summary.source_status == "reviewed" and not summary.warning
    ]
    reviewed_source_ids = {summary.source_id for summary in reviewed_sources}
    audit_source_ids = {record.source_id for record in audit_list.records}
    audited_reviewed_ids = sorted(reviewed_source_ids & audit_source_ids)
    unaudited_reviewed_ids = sorted(reviewed_source_ids - audit_source_ids)
    missing_ids = sorted({item for record in audit_list.records for item in record.missing_achievement_ids})
    blockers: list[str] = []
    warnings: list[str] = []
    next_steps: list[str] = []

    if not reviewed_sources:
        blockers.append("No reviewed achievement route source manifests are available.")
        next_steps.append("Promote at least one official fetch preview through the reviewed gate.")
    if not reviewed_steps:
        blockers.append("No reviewed route steps are available for planner ingestion.")
    if not audit_list.records:
        warnings.append("No promotion audit records exist yet; seed manifests may predate the audit gate.")
        next_steps.append("Run at least one reviewed promotion so release evidence includes reviewer metadata.")
    if missing_ids:
        warnings.append("Some promoted official fetch previews had missing achievement ids.")
        next_steps.append("Review missing achievement ids before treating the route pack as release-ready.")
    if unaudited_reviewed_ids:
        warnings.append("Some reviewed source manifests do not have promotion audit records.")
        next_steps.append("Backfill or re-promote reviewed source manifests through the audit gate where appropriate.")

    score = 100.0
    score -= len(blockers) * 35
    score -= min(len(warnings) * 10, 30)
    score += min(len(audited_reviewed_ids) * 5, 10)
    score = max(0.0, min(100.0, score))
    ready = not blockers and bool(reviewed_steps) and bool(audit_list.records) and not missing_ids
    maturity = "ready" if ready else "blocked" if blockers else "review_needed"
    if not next_steps and ready:
        next_steps.append("Route source release gate is ready; continue monitoring patch freshness and audit coverage.")

    return AchievementRouteReleaseReadiness(
        ready=ready,
        maturity_label=maturity,
        readiness_score=round(score, 1),
        reviewed_source_count=len(reviewed_sources),
        reviewed_step_count=len(reviewed_steps),
        promotion_audit_count=len(audit_list.records),
        promoted_source_count=len(audited_reviewed_ids),
        audited_source_ids=audited_reviewed_ids,
        unaudited_reviewed_source_ids=unaudited_reviewed_ids,
        missing_achievement_ids=missing_ids,
        blockers=blockers,
        warnings=warnings,
        next_steps=_unique(next_steps),
        evidence_chain=[
            "docs/knowledge_base/achievement_routes/*.json",
            "data/achievement_route_audit/promotion_audit.jsonl",
            "/api/v1/achievement-routes/sources",
            "/api/v1/achievement-routes/promotion-audit",
        ],
    )


def render_achievement_route_release_readiness_markdown(readiness: AchievementRouteReleaseReadiness) -> str:
    lines = [
        "# Achievement Route Release Readiness",
        "",
        f"- Ready: {readiness.ready}",
        f"- Maturity: {readiness.maturity_label}",
        f"- Score: {readiness.readiness_score}/100",
        f"- Reviewed sources: {readiness.reviewed_source_count}",
        f"- Reviewed steps: {readiness.reviewed_step_count}",
        f"- Promotion audit records: {readiness.promotion_audit_count}",
        f"- Boundary: {readiness.boundary}",
        "",
        "## Blockers",
    ]
    lines.extend([f"- {item}" for item in readiness.blockers] or ["- None"])
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {item}" for item in readiness.warnings] or ["- None"])
    lines.extend(["", "## Next Steps"])
    lines.extend([f"- {item}" for item in readiness.next_steps] or ["- None"])
    lines.extend(["", "## Evidence Chain"])
    lines.extend([f"- {item}" for item in readiness.evidence_chain])
    return "\n".join(lines) + "\n"


def render_achievement_route_release_readiness_csv(readiness: AchievementRouteReleaseReadiness) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "ready",
            "maturity_label",
            "readiness_score",
            "reviewed_source_count",
            "reviewed_step_count",
            "promotion_audit_count",
            "promoted_source_count",
            "blocker_count",
            "warning_count",
            "missing_achievement_ids",
        ]
    )
    writer.writerow(
        [
            readiness.ready,
            readiness.maturity_label,
            readiness.readiness_score,
            readiness.reviewed_source_count,
            readiness.reviewed_step_count,
            readiness.promotion_audit_count,
            readiness.promoted_source_count,
            len(readiness.blockers),
            len(readiness.warnings),
            ";".join(map(str, readiness.missing_achievement_ids)),
        ]
    )
    return buffer.getvalue()


def build_achievement_route_source_quality_review(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteSourceQualityReview:
    manifests = [
        manifest for manifest in load_achievement_route_source_manifests(source_root)
        if isinstance(manifest, AchievementRouteSourceManifest) and manifest.source_status == "reviewed"
    ]
    audit_list = list_achievement_route_promotion_audits(audit_root, limit=200)
    missing_ids = sorted({item for record in audit_list.records for item in record.missing_achievement_ids})
    source_reviews: list[AchievementRouteSourceQuality] = []
    step_reviews: list[AchievementRouteStepQuality] = []
    remediation: list[str] = []

    for manifest in manifests:
        source_step_reviews = [_review_route_step_quality(step, manifest, missing_ids) for step in manifest.steps]
        step_reviews.extend(source_step_reviews)
        average = _average([item.quality_score for item in source_step_reviews])
        high_risk_count = sum(1 for item in source_step_reviews if item.quality_score < 70)
        evidence_gap_count = sum(1 for item in source_step_reviews if not item.evidence_complete)
        map_risk_count = sum(1 for item in source_step_reviews if item.map_inference_risk != "low")
        gate_risk_count = sum(1 for item in source_step_reviews if item.time_gate_risk != "low")
        source_reviews.append(
            AchievementRouteSourceQuality(
                source_id=manifest.source_id,
                title=manifest.title,
                reviewed_by=manifest.reviewed_by,
                reviewed_at=manifest.reviewed_at,
                step_count=len(source_step_reviews),
                average_quality_score=average,
                high_risk_step_count=high_risk_count,
                evidence_gap_count=evidence_gap_count,
                map_inference_risk_count=map_risk_count,
                time_gate_risk_count=gate_risk_count,
            )
        )
    for step_review in step_reviews:
        remediation.extend(step_review.remediation)
    if missing_ids:
        remediation.append("Resolve or remove missing official achievement ids before release: " + ", ".join(map(str, missing_ids)) + ".")
    if not manifests:
        remediation.append("Add at least one reviewed achievement route source manifest.")
    overall = _average([item.quality_score for item in step_reviews])
    if not step_reviews:
        maturity = "blocked"
    elif overall >= 85 and not missing_ids and not any(item.high_risk_step_count for item in source_reviews):
        maturity = "ready"
    else:
        maturity = "review_needed"
    return AchievementRouteSourceQualityReview(
        overall_score=overall,
        maturity_label=maturity,
        source_reviews=source_reviews,
        step_reviews=step_reviews,
        missing_achievement_ids=missing_ids,
        remediation=_unique(remediation),
    )


def render_achievement_route_source_quality_markdown(review: AchievementRouteSourceQualityReview) -> str:
    lines = [
        "# Achievement Route Source Quality Review",
        "",
        f"- Maturity: {review.maturity_label}",
        f"- Overall score: {review.overall_score}/100",
        f"- Sources: {len(review.source_reviews)}",
        f"- Steps: {len(review.step_reviews)}",
        f"- Boundary: {review.boundary}",
        "",
        "## Sources",
        "| Source | Score | Steps | High Risk | Evidence Gaps | Map Risk | Time Gate Risk |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for source in review.source_reviews:
        lines.append(
            f"| {source.source_id} | {source.average_quality_score} | {source.step_count} | "
            f"{source.high_risk_step_count} | {source.evidence_gap_count} | "
            f"{source.map_inference_risk_count} | {source.time_gate_risk_count} |"
        )
    if not review.source_reviews:
        lines.append("| none | 0 | 0 | 0 | 0 | 0 | 0 |")
    lines.extend(["", "## Remediation"])
    lines.extend([f"- {item}" for item in review.remediation] or ["- None"])
    return "\n".join(lines) + "\n"


def render_achievement_route_source_quality_csv(review: AchievementRouteSourceQualityReview) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "step_id",
            "source_id",
            "quality_score",
            "evidence_complete",
            "map_inference_risk",
            "time_gate_risk",
            "missing_official_id",
            "review_flags",
            "remediation",
        ]
    )
    for step in review.step_reviews:
        writer.writerow(
            [
                step.step_id,
                step.source_id,
                step.quality_score,
                step.evidence_complete,
                step.map_inference_risk,
                step.time_gate_risk,
                step.missing_official_id,
                ";".join(step.review_flags),
                ";".join(step.remediation),
            ]
        )
    return buffer.getvalue()


def build_achievement_route_remediation_queue(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteRemediationQueue:
    quality = build_achievement_route_source_quality_review(source_root, audit_root)
    items: list[AchievementRouteRemediationItem] = []
    for step in quality.step_reviews:
        if "missing_official_achievement_id" in step.review_flags:
            items.append(
                _route_remediation_item(
                    remediation_type="official_id_backfill",
                    priority="P0",
                    step=step,
                    problem="The step references an official achievement id that the fetch audit reported missing.",
                    action="Re-fetch or replace the official achievement id, then re-run promotion review before release.",
                    prompt="Confirm whether the id was removed, renamed, region-locked, or entered incorrectly.",
                )
            )
        if "evidence_gap" in step.review_flags:
            items.append(
                _route_remediation_item(
                    remediation_type="evidence_backfill",
                    priority="P1",
                    step=step,
                    problem="The reviewed route step has no step-level evidence refs and no source-level refs.",
                    action="Add official wiki/API/patch evidence refs or remove the step from the reviewed manifest.",
                    prompt="Attach at least one source ref that proves the objective and route context.",
                )
            )
        if step.map_inference_risk == "high":
            items.append(
                _route_remediation_item(
                    remediation_type="map_review",
                    priority="P1",
                    step=step,
                    problem="The step map was not inferable from the official achievement payload.",
                    action="Confirm the map manually and update map_name/region, or keep the step as draft-only.",
                    prompt="Verify the achievement panel, official wiki page, or in-game map before promoting.",
                )
            )
        elif step.map_inference_risk == "medium":
            items.append(
                _route_remediation_item(
                    remediation_type="map_review",
                    priority="P2",
                    step=step,
                    problem="The step map was inferred from text and should be checked before broad release.",
                    action="Spot-check the inferred map and add the evidence ref used for the inference.",
                    prompt="Confirm the inferred map is still accurate after the current patch.",
                )
            )
        if step.time_gate_risk != "low":
            items.append(
                _route_remediation_item(
                    remediation_type="time_gate_review",
                    priority="P2",
                    step=step,
                    problem="The step is daily or weekly gated and may need current reset/rotation context.",
                    action="Add current reset or rotation review notes before recommending the step in a session plan.",
                    prompt="Confirm whether the gate is account-wide, daily, weekly, or event/patch dependent.",
                )
            )
    covered_missing_ids = {item.official_achievement_id for item in quality.step_reviews if item.missing_official_id}
    for missing_id in quality.missing_achievement_ids:
        if missing_id in covered_missing_ids:
            continue
        items.append(
            AchievementRouteRemediationItem(
                item_id=f"p0:official-id-backfill:missing:{missing_id}",
                priority="P0",
                remediation_type="official_id_backfill",
                title=f"Resolve missing official achievement id {missing_id}",
                problem="The promotion audit reported a requested official achievement id that was not returned by the gateway.",
                recommended_action="Re-fetch the id, replace it with the current official id, or document why it should be excluded before release.",
                reviewer_prompt="Confirm whether the id is invalid, removed, region-dependent, or a data-entry issue.",
                evidence_refs=[
                    f"official-achievement-id:{missing_id}",
                    "data/achievement_route_audit/promotion_audit.jsonl",
                    "/api/v1/achievement-routes/promotion-audit",
                ],
            )
        )
    if not quality.source_reviews:
        items.append(
            AchievementRouteRemediationItem(
                item_id="source-manifest-backfill",
                priority="P0",
                remediation_type="source_manifest_backfill",
                title="Add reviewed achievement route source manifests",
                problem="No reviewed achievement route source manifests are available.",
                recommended_action="Promote reviewed official fetch previews or add reviewed source manifests before release.",
                reviewer_prompt="Confirm at least one reviewed source has evidence refs, reviewer, reviewed_at, and route steps.",
                evidence_refs=["docs/knowledge_base/achievement_routes/*.json"],
            )
        )
    items = sorted(items, key=lambda item: ({"P0": 0, "P1": 1, "P2": 2}[item.priority], item.source_id or "", item.step_id or "", item.remediation_type))
    return AchievementRouteRemediationQueue(
        maturity_label=quality.maturity_label,
        open_item_count=len(items),
        p0_count=sum(1 for item in items if item.priority == "P0"),
        p1_count=sum(1 for item in items if item.priority == "P1"),
        p2_count=sum(1 for item in items if item.priority == "P2"),
        items=items,
        next_actions=_route_remediation_next_actions(items),
        evidence_chain=[
            "/api/v1/achievement-routes/source-quality",
            "docs/knowledge_base/achievement_routes/*.json",
            "data/achievement_route_audit/promotion_audit.jsonl",
        ],
    )


def render_achievement_route_remediation_queue_markdown(queue: AchievementRouteRemediationQueue) -> str:
    lines = [
        "# Achievement Route Remediation Queue",
        "",
        f"- Maturity: {queue.maturity_label}",
        f"- Open items: {queue.open_item_count}",
        f"- P0: {queue.p0_count}",
        f"- P1: {queue.p1_count}",
        f"- P2: {queue.p2_count}",
        f"- Boundary: {queue.boundary}",
        "",
        "## Items",
    ]
    for item in queue.items:
        lines.extend(
            [
                f"### {item.priority} {item.title}",
                f"- Type: {item.remediation_type}",
                f"- Source: {item.source_id or 'n/a'}",
                f"- Step: {item.step_id or 'n/a'}",
                f"- Problem: {item.problem}",
                f"- Action: {item.recommended_action}",
                f"- Reviewer prompt: {item.reviewer_prompt}",
                f"- Evidence: {', '.join(item.evidence_refs) if item.evidence_refs else 'pending'}",
                "",
            ]
        )
    if not queue.items:
        lines.append("- None")
    lines.extend(["", "## Next Actions"])
    lines.extend([f"- {action}" for action in queue.next_actions] or ["- None"])
    lines.extend(["", "## Evidence Chain"])
    lines.extend([f"- {ref}" for ref in queue.evidence_chain])
    return "\n".join(lines) + "\n"


def render_achievement_route_remediation_queue_csv(queue: AchievementRouteRemediationQueue) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "item_id",
            "priority",
            "remediation_type",
            "status",
            "source_id",
            "step_id",
            "title",
            "problem",
            "recommended_action",
            "reviewer_prompt",
            "evidence_refs",
        ]
    )
    for item in queue.items:
        writer.writerow(
            [
                item.item_id,
                item.priority,
                item.remediation_type,
                item.status,
                item.source_id or "",
                item.step_id or "",
                item.title,
                item.problem,
                item.recommended_action,
                item.reviewer_prompt,
                ";".join(item.evidence_refs),
            ]
        )
    return buffer.getvalue()


def record_achievement_route_remediation_review(
    request: AchievementRouteRemediationReviewRequest,
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteRemediationReviewRecord:
    if not request.confirmed_manual_review:
        raise ValueError("Remediation review requires confirmed_manual_review=true.")
    queue = build_achievement_route_remediation_queue(source_root, audit_root)
    item_by_id = {item.item_id: item for item in queue.items}
    item = item_by_id.get(request.item_id)
    if item is None:
        raise ValueError(f"Remediation item {request.item_id} is not present in the current review queue.")
    record = AchievementRouteRemediationReviewRecord(
        event_id=f"route-remediation-review:{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
        item_id=request.item_id,
        status=request.status,
        occurred_at=datetime.now(UTC),
        reviewer=request.reviewer,
        notes=_unique([note.strip() for note in request.notes if note.strip()]),
        evidence_refs=_unique([*item.evidence_refs, *[ref.strip() for ref in request.evidence_refs if ref.strip()]]),
        source_id=item.source_id,
        step_id=item.step_id,
        remediation_type=item.remediation_type,
        priority=item.priority,
    )
    audit_root.mkdir(parents=True, exist_ok=True)
    path = audit_root / "remediation_review_audit.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(record.model_dump_json() + "\n")
    return record


def list_achievement_route_remediation_review_audits(
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    *,
    reviewer: str | None = None,
    status: RouteRemediationReviewStatus | None = None,
    item_id: str | None = None,
    limit: int = 25,
) -> AchievementRouteRemediationReviewAuditList:
    path = audit_root / "remediation_review_audit.jsonl"
    records: list[AchievementRouteRemediationReviewRecord] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = AchievementRouteRemediationReviewRecord.model_validate_json(line)
            except ValidationError:
                continue
            if reviewer and record.reviewer != reviewer:
                continue
            if status and record.status != status:
                continue
            if item_id and record.item_id != item_id:
                continue
            records.append(record)
    records = sorted(records, key=lambda item: item.occurred_at, reverse=True)[: max(1, min(limit, 200))]
    return AchievementRouteRemediationReviewAuditList(
        records=records,
        filters={"reviewer": reviewer, "status": status, "item_id": item_id, "limit": limit},
    )


def render_achievement_route_remediation_review_audit_markdown(audit_list: AchievementRouteRemediationReviewAuditList) -> str:
    lines = [
        "# Achievement Route Remediation Review Audit",
        "",
        f"- Records: {len(audit_list.records)}",
        f"- Boundary: {audit_list.boundary}",
        "",
        "| Occurred At | Reviewer | Status | Priority | Type | Item | Source | Step |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in audit_list.records:
        lines.append(
            "| "
            + " | ".join(
                [
                    record.occurred_at.isoformat(),
                    record.reviewer,
                    record.status,
                    record.priority or "n/a",
                    record.remediation_type or "n/a",
                    record.item_id,
                    record.source_id or "n/a",
                    record.step_id or "n/a",
                ]
            )
            + " |"
        )
    if not audit_list.records:
        lines.append("| none | none | none | none | none | none | none | none |")
    return "\n".join(lines) + "\n"


def render_achievement_route_remediation_review_audit_csv(audit_list: AchievementRouteRemediationReviewAuditList) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "event_id",
            "occurred_at",
            "reviewer",
            "status",
            "priority",
            "remediation_type",
            "item_id",
            "source_id",
            "step_id",
            "notes",
            "evidence_refs",
        ]
    )
    for record in audit_list.records:
        writer.writerow(
            [
                record.event_id,
                record.occurred_at.isoformat(),
                record.reviewer,
                record.status,
                record.priority or "",
                record.remediation_type or "",
                record.item_id,
                record.source_id or "",
                record.step_id or "",
                ";".join(record.notes),
                ";".join(record.evidence_refs),
            ]
        )
    return buffer.getvalue()


def build_achievement_route_remediation_readiness(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteRemediationReadiness:
    queue = build_achievement_route_remediation_queue(source_root, audit_root)
    audit = list_achievement_route_remediation_review_audits(audit_root, limit=200)
    latest_by_item: dict[str, AchievementRouteRemediationReviewRecord] = {}
    for record in sorted(audit.records, key=lambda item: item.occurred_at):
        latest_by_item[record.item_id] = record

    unresolved_item_ids: list[str] = []
    deferred_item_ids: list[str] = []
    resolved_without_extra_evidence: list[str] = []
    resolved_count = 0
    acknowledged_count = 0
    deferred_count = 0
    reviewed_count = 0

    for item in queue.items:
        record = latest_by_item.get(item.item_id)
        if record is None:
            unresolved_item_ids.append(item.item_id)
            continue
        reviewed_count += 1
        if record.status == "resolved":
            resolved_count += 1
            extra_evidence = [ref for ref in record.evidence_refs if ref not in item.evidence_refs]
            if not extra_evidence:
                resolved_without_extra_evidence.append(item.item_id)
        elif record.status == "acknowledged":
            acknowledged_count += 1
            unresolved_item_ids.append(item.item_id)
        elif record.status == "deferred":
            deferred_count += 1
            deferred_item_ids.append(item.item_id)
            unresolved_item_ids.append(item.item_id)

    open_p0 = sum(1 for item in queue.items if item.priority == "P0" and item.item_id in unresolved_item_ids)
    open_p1 = sum(1 for item in queue.items if item.priority == "P1" and item.item_id in unresolved_item_ids)
    open_p2 = sum(1 for item in queue.items if item.priority == "P2" and item.item_id in unresolved_item_ids)
    blockers: list[str] = []
    warnings: list[str] = []
    next_steps: list[str] = []
    if open_p0:
        blockers.append(f"{open_p0} P0 remediation items remain unresolved.")
        next_steps.append("Resolve all P0 remediation items before release.")
    if open_p1:
        blockers.append(f"{open_p1} P1 remediation items remain unresolved.")
        next_steps.append("Resolve or explicitly defer P1 remediation items with reviewer notes.")
    if deferred_item_ids:
        warnings.append("Some remediation items are deferred and require release-owner acceptance.")
        next_steps.append("Review deferred item risk before go/no-go.")
    if resolved_without_extra_evidence:
        warnings.append("Some resolved remediation reviews did not add evidence beyond queue evidence refs.")
        next_steps.append("Add explicit evidence refs to resolved remediation reviews where possible.")
    if not queue.items:
        next_steps.append("No remediation queue items are open; continue source quality and release readiness checks.")

    score = 100.0
    score -= open_p0 * 35
    score -= open_p1 * 20
    score -= min(open_p2 * 5, 20)
    score -= min(len(deferred_item_ids) * 10, 30)
    score -= min(len(resolved_without_extra_evidence) * 5, 20)
    score = max(0.0, min(100.0, score))
    ready = not blockers and not deferred_item_ids and not resolved_without_extra_evidence
    if queue.items and reviewed_count < len(queue.items):
        ready = False
    maturity = "ready" if ready else "blocked" if blockers else "review_needed"
    if not next_steps and ready:
        next_steps.append("Remediation readiness is ready; continue release readiness and patch freshness review.")

    return AchievementRouteRemediationReadiness(
        ready=ready,
        maturity_label=maturity,
        readiness_score=round(score, 1),
        queue_item_count=len(queue.items),
        open_p0_count=open_p0,
        open_p1_count=open_p1,
        open_p2_count=open_p2,
        reviewed_item_count=reviewed_count,
        resolved_count=resolved_count,
        acknowledged_count=acknowledged_count,
        deferred_count=deferred_count,
        unresolved_item_ids=_unique(unresolved_item_ids),
        deferred_item_ids=_unique(deferred_item_ids),
        resolved_without_extra_evidence_item_ids=_unique(resolved_without_extra_evidence),
        blockers=blockers,
        warnings=warnings,
        next_steps=_unique(next_steps),
        evidence_chain=[
            "/api/v1/achievement-routes/source-quality/remediation-queue",
            "/api/v1/achievement-routes/source-quality/remediation-queue/review-audit",
            "data/achievement_route_audit/remediation_review_audit.jsonl",
        ],
    )


def render_achievement_route_remediation_readiness_markdown(readiness: AchievementRouteRemediationReadiness) -> str:
    lines = [
        "# Achievement Route Remediation Readiness",
        "",
        f"- Ready: {readiness.ready}",
        f"- Maturity: {readiness.maturity_label}",
        f"- Score: {readiness.readiness_score}/100",
        f"- Queue items: {readiness.queue_item_count}",
        f"- Reviewed items: {readiness.reviewed_item_count}",
        f"- Open P0/P1/P2: {readiness.open_p0_count}/{readiness.open_p1_count}/{readiness.open_p2_count}",
        f"- Resolved/Acknowledged/Deferred: {readiness.resolved_count}/{readiness.acknowledged_count}/{readiness.deferred_count}",
        f"- Boundary: {readiness.boundary}",
        "",
        "## Blockers",
    ]
    lines.extend([f"- {item}" for item in readiness.blockers] or ["- None"])
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {item}" for item in readiness.warnings] or ["- None"])
    lines.extend(["", "## Next Steps"])
    lines.extend([f"- {item}" for item in readiness.next_steps] or ["- None"])
    lines.extend(["", "## Evidence Chain"])
    lines.extend([f"- {item}" for item in readiness.evidence_chain])
    return "\n".join(lines) + "\n"


def render_achievement_route_remediation_readiness_csv(readiness: AchievementRouteRemediationReadiness) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "ready",
            "maturity_label",
            "readiness_score",
            "queue_item_count",
            "open_p0_count",
            "open_p1_count",
            "open_p2_count",
            "reviewed_item_count",
            "resolved_count",
            "acknowledged_count",
            "deferred_count",
            "unresolved_item_ids",
            "deferred_item_ids",
            "resolved_without_extra_evidence_item_ids",
        ]
    )
    writer.writerow(
        [
            readiness.ready,
            readiness.maturity_label,
            readiness.readiness_score,
            readiness.queue_item_count,
            readiness.open_p0_count,
            readiness.open_p1_count,
            readiness.open_p2_count,
            readiness.reviewed_item_count,
            readiness.resolved_count,
            readiness.acknowledged_count,
            readiness.deferred_count,
            ";".join(readiness.unresolved_item_ids),
            ";".join(readiness.deferred_item_ids),
            ";".join(readiness.resolved_without_extra_evidence_item_ids),
        ]
    )
    return buffer.getvalue()


def build_achievement_route_operator_action_bundle(
    request: AchievementRouteOperatorActionBundleRequest | None = None,
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteOperatorActionBundle:
    remediation_review: AchievementRouteRemediationReviewRecord | None = None
    if request and request.review:
        remediation_review = record_achievement_route_remediation_review(request.review, source_root, audit_root)
    quality = build_achievement_route_source_quality_review(source_root, audit_root)
    queue = build_achievement_route_remediation_queue(source_root, audit_root)
    review_audit = list_achievement_route_remediation_review_audits(audit_root, limit=50)
    remediation_readiness = build_achievement_route_remediation_readiness(source_root, audit_root)
    release_readiness = build_achievement_route_release_readiness(source_root, audit_root)
    next_actions = [
        *remediation_readiness.next_steps,
        *release_readiness.next_steps,
    ]
    if remediation_review:
        next_actions.insert(0, f"Review action recorded for {remediation_review.item_id} as {remediation_review.status}.")
    return AchievementRouteOperatorActionBundle(
        quality=quality,
        remediation_queue=queue,
        remediation_review=remediation_review,
        remediation_review_audit=review_audit,
        remediation_readiness=remediation_readiness,
        release_readiness=release_readiness,
        next_actions=_unique(next_actions),
    )


def render_achievement_route_operator_action_bundle_markdown(bundle: AchievementRouteOperatorActionBundle) -> str:
    lines = [
        "# Achievement Route Operator Action Bundle",
        "",
        f"- Quality: {bundle.quality.maturity_label} {bundle.quality.overall_score}/100",
        f"- Remediation queue items: {bundle.remediation_queue.open_item_count}",
        f"- Review audit records: {len(bundle.remediation_review_audit.records)}",
        f"- Remediation readiness: {bundle.remediation_readiness.maturity_label} {bundle.remediation_readiness.readiness_score}/100",
        f"- Release readiness: {bundle.release_readiness.maturity_label} {bundle.release_readiness.readiness_score}/100",
        f"- Boundary: {bundle.boundary}",
        "",
        "## Latest Review Action",
    ]
    if bundle.remediation_review:
        lines.extend(
            [
                f"- Item: {bundle.remediation_review.item_id}",
                f"- Status: {bundle.remediation_review.status}",
                f"- Reviewer: {bundle.remediation_review.reviewer}",
            ]
        )
    else:
        lines.append("- None")
    lines.extend(["", "## Next Actions"])
    lines.extend([f"- {action}" for action in bundle.next_actions] or ["- None"])
    return "\n".join(lines) + "\n"


def render_achievement_route_operator_action_bundle_csv(bundle: AchievementRouteOperatorActionBundle) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "quality_maturity",
            "quality_score",
            "queue_item_count",
            "review_audit_count",
            "remediation_readiness_maturity",
            "remediation_readiness_score",
            "release_readiness_maturity",
            "release_readiness_score",
            "latest_review_item_id",
            "latest_review_status",
        ]
    )
    writer.writerow(
        [
            bundle.quality.maturity_label,
            bundle.quality.overall_score,
            bundle.remediation_queue.open_item_count,
            len(bundle.remediation_review_audit.records),
            bundle.remediation_readiness.maturity_label,
            bundle.remediation_readiness.readiness_score,
            bundle.release_readiness.maturity_label,
            bundle.release_readiness.readiness_score,
            bundle.remediation_review.item_id if bundle.remediation_review else "",
            bundle.remediation_review.status if bundle.remediation_review else "",
        ]
    )
    return buffer.getvalue()


def build_achievement_route_operator_release_packet(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteOperatorReleasePacket:
    bundle = build_achievement_route_operator_action_bundle(None, source_root, audit_root)
    blockers = [*bundle.remediation_readiness.blockers, *bundle.release_readiness.blockers]
    warnings = [*bundle.remediation_readiness.warnings, *bundle.release_readiness.warnings, *bundle.quality.remediation]
    ready = bundle.remediation_readiness.ready and bundle.release_readiness.ready and bundle.quality.maturity_label == "ready"
    maturity = "ready" if ready else "blocked" if blockers else "review_needed"
    generated_at = datetime.now(UTC)
    manifest = {
        "packet_schema": "gw2radar.achievement_route_operator_release_packet.v1",
        "generated_at": generated_at.isoformat(),
        "artifacts": [
            "operator_release_packet.md",
            "operator_release_packet.csv",
            "operator_release_packet_manifest.json",
        ],
        "source_paths": [
            "docs/knowledge_base/achievement_routes/*.json",
            "data/achievement_route_audit/promotion_audit.jsonl",
            "data/achievement_route_audit/remediation_review_audit.jsonl",
        ],
        "api_refs": [
            "/api/v1/achievement-routes/source-quality/remediation-queue/action-bundle",
            "/api/v1/achievement-routes/source-quality/remediation-queue/readiness",
            "/api/v1/achievement-routes/release-readiness",
        ],
        "safety_boundaries": [
            "No raw API keys or private account payloads are included.",
            "No source manifests are edited by this packet.",
            "No gameplay, trading, or publishing action is automated.",
        ],
    }
    return AchievementRouteOperatorReleasePacket(
        packet_id=f"achievement-route-release:{generated_at.strftime('%Y%m%d%H%M%S')}",
        generated_at=generated_at,
        ready=ready,
        maturity_label=maturity,
        quality_score=bundle.quality.overall_score,
        remediation_score=bundle.remediation_readiness.readiness_score,
        release_score=bundle.release_readiness.readiness_score,
        open_remediation_items=bundle.remediation_queue.open_item_count,
        blocker_count=len(blockers),
        warning_count=len(warnings),
        manifest=manifest,
        bundle=bundle,
    )


def render_achievement_route_operator_release_packet_markdown(packet: AchievementRouteOperatorReleasePacket) -> str:
    lines = [
        "# Achievement Route Operator Release Packet",
        "",
        f"- Packet: {packet.packet_id}",
        f"- Ready: {packet.ready}",
        f"- Maturity: {packet.maturity_label}",
        f"- Quality score: {packet.quality_score}/100",
        f"- Remediation score: {packet.remediation_score}/100",
        f"- Release score: {packet.release_score}/100",
        f"- Open remediation items: {packet.open_remediation_items}",
        f"- Blockers: {packet.blocker_count}",
        f"- Warnings: {packet.warning_count}",
        f"- Boundary: {packet.boundary}",
        "",
        "## Blockers",
    ]
    blockers = [*packet.bundle.remediation_readiness.blockers, *packet.bundle.release_readiness.blockers]
    lines.extend([f"- {item}" for item in blockers] or ["- None"])
    lines.extend(["", "## Warnings"])
    warnings = [*packet.bundle.remediation_readiness.warnings, *packet.bundle.release_readiness.warnings]
    lines.extend([f"- {item}" for item in warnings] or ["- None"])
    lines.extend(["", "## Manifest Artifacts"])
    lines.extend([f"- {item}" for item in packet.manifest.get("artifacts", [])])
    lines.extend(["", "## Next Actions"])
    lines.extend([f"- {item}" for item in packet.bundle.next_actions] or ["- None"])
    return "\n".join(lines) + "\n"


def render_achievement_route_operator_release_packet_csv(packet: AchievementRouteOperatorReleasePacket) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "packet_id",
            "ready",
            "maturity_label",
            "quality_score",
            "remediation_score",
            "release_score",
            "open_remediation_items",
            "blocker_count",
            "warning_count",
        ]
    )
    writer.writerow(
        [
            packet.packet_id,
            packet.ready,
            packet.maturity_label,
            packet.quality_score,
            packet.remediation_score,
            packet.release_score,
            packet.open_remediation_items,
            packet.blocker_count,
            packet.warning_count,
        ]
    )
    return buffer.getvalue()


def build_achievement_route_unified_release_evidence_bundle(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteUnifiedReleaseEvidenceBundle:
    release_readiness = build_achievement_route_release_readiness(source_root, audit_root)
    quality = build_achievement_route_source_quality_review(source_root, audit_root)
    packet = build_achievement_route_operator_release_packet(source_root, audit_root)
    official_audit = list_achievement_route_promotion_audits(audit_root, limit=200)
    patch_apply_audit = list_achievement_route_source_edit_patch_apply_audits(audit_root, limit=200)
    draft_promotion_audit = list_achievement_route_draft_source_promotion_audits(audit_root, limit=200)
    source_ids = _unique([review.source_id for review in quality.source_reviews])
    blockers = [*release_readiness.blockers, *packet.bundle.remediation_readiness.blockers]
    warnings = [*release_readiness.warnings, *quality.remediation, *packet.bundle.remediation_readiness.warnings]
    artifacts = [
        "unified_release_evidence_bundle.md",
        "unified_release_evidence_bundle.csv",
        "unified_release_evidence_bundle_manifest.json",
        "operator_release_packet.md",
        "promotion_audit.csv",
        "source_patch_apply_audit.csv",
        "draft_source_promotion_audit.csv",
    ]
    generated_at = datetime.now(UTC)
    ready = release_readiness.ready and packet.ready and quality.maturity_label == "ready"
    maturity = "ready" if ready else "blocked" if blockers else "review_needed"
    manifest = {
        "bundle_schema": "gw2radar.achievement_route_unified_release_evidence_bundle.v1",
        "bundle_id": f"route-release-evidence:{generated_at.strftime('%Y%m%d%H%M%S')}",
        "generated_at": generated_at.isoformat(),
        "ready": ready,
        "maturity_label": maturity,
        "artifacts": artifacts,
        "source_ids": source_ids,
        "audit_sources": [
            "data/achievement_route_audit/promotion_audit.jsonl",
            "data/achievement_route_audit/source_edit_patch_apply_audit.jsonl",
            "data/achievement_route_audit/draft_source_promotion_audit.jsonl",
            "data/achievement_route_audit/remediation_review_audit.jsonl",
        ],
        "safety_boundary": "Read-only evidence handoff; no source edit, publish, gameplay automation, or live-state certification.",
    }
    return AchievementRouteUnifiedReleaseEvidenceBundle(
        bundle_id=manifest["bundle_id"],
        generated_at=generated_at,
        ready=ready,
        maturity_label=maturity,
        reviewed_source_count=release_readiness.reviewed_source_count,
        reviewed_step_count=release_readiness.reviewed_step_count,
        official_promotion_audit_count=len(official_audit.records),
        patch_apply_audit_count=len(patch_apply_audit.records),
        draft_source_promotion_audit_count=len(draft_promotion_audit.records),
        quality_score=quality.overall_score,
        release_score=release_readiness.readiness_score,
        remediation_score=packet.remediation_score,
        blocker_count=len(_unique(blockers)),
        warning_count=len(_unique(warnings)),
        source_ids=source_ids,
        artifacts=artifacts,
        evidence_chain=[
            "/api/v1/achievement-routes/release-readiness",
            "/api/v1/achievement-routes/source-quality",
            "/api/v1/achievement-routes/promotion-audit",
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-packet",
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply-audit",
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/promote-draft-source-audit",
        ],
        manifest=manifest,
        release_readiness=release_readiness,
        quality=quality,
        operator_release_packet=packet,
        official_promotion_audit=official_audit,
        source_patch_apply_audit=patch_apply_audit,
        draft_source_promotion_audit=draft_promotion_audit,
    )


def render_achievement_route_unified_release_evidence_bundle_markdown(
    bundle: AchievementRouteUnifiedReleaseEvidenceBundle,
) -> str:
    lines = [
        "# Achievement Route Unified Release Evidence Bundle",
        "",
        f"- Bundle: {bundle.bundle_id}",
        f"- Ready: {bundle.ready}",
        f"- Maturity: {bundle.maturity_label}",
        f"- Reviewed sources: {bundle.reviewed_source_count}",
        f"- Reviewed steps: {bundle.reviewed_step_count}",
        f"- Quality score: {bundle.quality_score}/100",
        f"- Release score: {bundle.release_score}/100",
        f"- Remediation score: {bundle.remediation_score}/100",
        f"- Official promotion audits: {bundle.official_promotion_audit_count}",
        f"- Patch apply audits: {bundle.patch_apply_audit_count}",
        f"- Draft source promotion audits: {bundle.draft_source_promotion_audit_count}",
        f"- Blockers: {bundle.blocker_count}",
        f"- Warnings: {bundle.warning_count}",
        f"- Boundary: {bundle.boundary}",
        "",
        "## Source IDs",
    ]
    lines.extend([f"- {source_id}" for source_id in bundle.source_ids] or ["- None"])
    lines.extend(["", "## Release Readiness Blockers"])
    lines.extend([f"- {item}" for item in bundle.release_readiness.blockers] or ["- None"])
    lines.extend(["", "## Source Quality Remediation"])
    lines.extend([f"- {item}" for item in bundle.quality.remediation] or ["- None"])
    lines.extend(["", "## Evidence Chain"])
    lines.extend([f"- {item}" for item in bundle.evidence_chain])
    lines.extend(["", "## Artifacts"])
    lines.extend([f"- {item}" for item in bundle.artifacts])
    return "\n".join(lines) + "\n"


def render_achievement_route_unified_release_evidence_bundle_csv(
    bundle: AchievementRouteUnifiedReleaseEvidenceBundle,
) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "bundle_id",
            "ready",
            "maturity_label",
            "reviewed_source_count",
            "reviewed_step_count",
            "quality_score",
            "release_score",
            "remediation_score",
            "official_promotion_audit_count",
            "patch_apply_audit_count",
            "draft_source_promotion_audit_count",
            "blocker_count",
            "warning_count",
            "source_ids",
        ]
    )
    writer.writerow(
        [
            bundle.bundle_id,
            bundle.ready,
            bundle.maturity_label,
            bundle.reviewed_source_count,
            bundle.reviewed_step_count,
            bundle.quality_score,
            bundle.release_score,
            bundle.remediation_score,
            bundle.official_promotion_audit_count,
            bundle.patch_apply_audit_count,
            bundle.draft_source_promotion_audit_count,
            bundle.blocker_count,
            bundle.warning_count,
            ";".join(bundle.source_ids),
        ]
    )
    return buffer.getvalue()


def archive_achievement_route_release_evidence_bundle(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    *,
    archived_by: str = "local_operator",
    retention_policy: str = "retain_365_days",
) -> AchievementRouteReleaseEvidenceArchiveRecord:
    bundle = build_achievement_route_unified_release_evidence_bundle(source_root, audit_root)
    archived_at = datetime.now(UTC)
    canonical_bundle = json.dumps(bundle.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    checksum = hashlib.sha256(canonical_bundle.encode("utf-8")).hexdigest()
    archive_id = f"achievement-route-release-archive:{archived_at.strftime('%Y%m%dT%H%M%S%fZ')}:{checksum[:12]}"
    record = AchievementRouteReleaseEvidenceArchiveRecord(
        archive_id=archive_id,
        bundle_id=bundle.bundle_id,
        archived_at=archived_at,
        generated_at=bundle.generated_at,
        archived_by=archived_by,
        checksum_sha256=checksum,
        retention_policy=retention_policy,
        ready=bundle.ready,
        maturity_label=bundle.maturity_label,
        reviewed_source_count=bundle.reviewed_source_count,
        reviewed_step_count=bundle.reviewed_step_count,
        blocker_count=bundle.blocker_count,
        warning_count=bundle.warning_count,
        source_ids=bundle.source_ids,
        artifacts=bundle.artifacts,
        evidence_chain=bundle.evidence_chain,
        manifest_schema=str(bundle.manifest.get("bundle_schema", "")),
        source_bundle_schema=bundle.schema_version,
    )
    audit_root.mkdir(parents=True, exist_ok=True)
    path = audit_root / "release_evidence_archive.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(record.model_dump_json() + "\n")
    return record


def list_achievement_route_release_evidence_archives(
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    *,
    archived_by: str | None = None,
    maturity_label: str | None = None,
    limit: int = 25,
) -> AchievementRouteReleaseEvidenceArchiveIndex:
    path = audit_root / "release_evidence_archive.jsonl"
    records: list[AchievementRouteReleaseEvidenceArchiveRecord] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = AchievementRouteReleaseEvidenceArchiveRecord.model_validate_json(line)
            except ValidationError:
                continue
            if archived_by and record.archived_by != archived_by:
                continue
            if maturity_label and record.maturity_label != maturity_label:
                continue
            records.append(record)
    records = sorted(records, key=lambda item: item.archived_at, reverse=True)[: max(1, min(limit, 200))]
    return AchievementRouteReleaseEvidenceArchiveIndex(
        records=records,
        filters={"archived_by": archived_by, "maturity_label": maturity_label, "limit": limit},
        total_records=len(records),
        latest_archive_id=records[0].archive_id if records else None,
    )


def render_achievement_route_release_evidence_archive_markdown(
    index: AchievementRouteReleaseEvidenceArchiveIndex,
) -> str:
    lines = [
        "# Achievement Route Release Evidence Archive",
        "",
        f"- Records: {index.total_records}",
        f"- Latest archive: {index.latest_archive_id or 'None'}",
        f"- Boundary: {index.boundary}",
        "",
        "## Records",
    ]
    if not index.records:
        lines.append("- None")
    for record in index.records:
        lines.extend(
            [
                f"- Archive: {record.archive_id}",
                f"  - Bundle: {record.bundle_id}",
                f"  - Archived by: {record.archived_by}",
                f"  - Maturity: {record.maturity_label}",
                f"  - Checksum: {record.checksum_sha256}",
                f"  - Retention: {record.retention_policy}",
                f"  - Reviewed sources: {record.reviewed_source_count}",
                f"  - Blockers: {record.blocker_count}",
            ]
        )
    return "\n".join(lines) + "\n"


def render_achievement_route_release_evidence_archive_csv(
    index: AchievementRouteReleaseEvidenceArchiveIndex,
) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "archive_id",
            "bundle_id",
            "archived_at",
            "archived_by",
            "checksum_sha256",
            "retention_policy",
            "ready",
            "maturity_label",
            "reviewed_source_count",
            "reviewed_step_count",
            "blocker_count",
            "warning_count",
            "source_ids",
        ]
    )
    for record in index.records:
        writer.writerow(
            [
                record.archive_id,
                record.bundle_id,
                record.archived_at.isoformat(),
                record.archived_by,
                record.checksum_sha256,
                record.retention_policy,
                record.ready,
                record.maturity_label,
                record.reviewed_source_count,
                record.reviewed_step_count,
                record.blocker_count,
                record.warning_count,
                ";".join(record.source_ids),
            ]
        )
    return buffer.getvalue()


def build_achievement_route_release_evidence_archive_diff(
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    *,
    baseline_archive_id: str | None = None,
    candidate_archive_id: str | None = None,
) -> AchievementRouteReleaseEvidenceArchiveDiff:
    index = list_achievement_route_release_evidence_archives(audit_root, limit=200)
    records_by_id = {record.archive_id: record for record in index.records}
    if baseline_archive_id:
        baseline = records_by_id.get(baseline_archive_id)
    else:
        baseline = index.records[1] if len(index.records) > 1 else None
    if candidate_archive_id:
        candidate = records_by_id.get(candidate_archive_id)
    else:
        candidate = index.records[0] if index.records else None

    generated_at = datetime.now(UTC)
    if baseline is None or candidate is None:
        return AchievementRouteReleaseEvidenceArchiveDiff(
            generated_at=generated_at,
            baseline_archive_id=baseline.archive_id if baseline else baseline_archive_id,
            candidate_archive_id=candidate.archive_id if candidate else candidate_archive_id,
            ready=False,
            maturity_label="review_needed",
            regression_count=0,
            improvement_count=0,
            unchanged_count=0,
            findings=["At least two release evidence archives are required for diff review."],
            next_actions=["Archive the current release evidence bundle twice across meaningful review points before diffing."],
        )

    source_added, source_removed = _set_delta(candidate.source_ids, baseline.source_ids)
    artifact_added, artifact_removed = _set_delta(candidate.artifacts, baseline.artifacts)
    evidence_added, evidence_removed = _set_delta(candidate.evidence_chain, baseline.evidence_chain)
    metric_deltas = {
        "reviewed_source_count": candidate.reviewed_source_count - baseline.reviewed_source_count,
        "reviewed_step_count": candidate.reviewed_step_count - baseline.reviewed_step_count,
        "blocker_count": candidate.blocker_count - baseline.blocker_count,
        "warning_count": candidate.warning_count - baseline.warning_count,
    }
    checksum_changed = candidate.checksum_sha256 != baseline.checksum_sha256
    maturity_changed = candidate.maturity_label != baseline.maturity_label
    regressions: list[str] = []
    improvements: list[str] = []
    findings: list[str] = []
    next_actions: list[str] = []

    if metric_deltas["blocker_count"] > 0:
        regressions.append(f"Blocker count increased by {metric_deltas['blocker_count']}.")
    if metric_deltas["warning_count"] > 0:
        regressions.append(f"Warning count increased by {metric_deltas['warning_count']}.")
    if source_removed:
        regressions.append("Reviewed source ids were removed: " + ", ".join(source_removed) + ".")
    if artifact_removed:
        regressions.append("Release artifacts were removed: " + ", ".join(artifact_removed) + ".")
    if evidence_removed:
        regressions.append("Evidence chain refs were removed: " + ", ".join(evidence_removed) + ".")
    if candidate.maturity_label == "blocked" and baseline.maturity_label != "blocked":
        regressions.append("Maturity regressed to blocked.")

    if metric_deltas["blocker_count"] < 0:
        improvements.append(f"Blocker count decreased by {abs(metric_deltas['blocker_count'])}.")
    if metric_deltas["warning_count"] < 0:
        improvements.append(f"Warning count decreased by {abs(metric_deltas['warning_count'])}.")
    if source_added:
        improvements.append("Reviewed source ids were added: " + ", ".join(source_added) + ".")
    if artifact_added:
        improvements.append("Release artifacts were added: " + ", ".join(artifact_added) + ".")
    if evidence_added:
        improvements.append("Evidence chain refs were added: " + ", ".join(evidence_added) + ".")
    if candidate.maturity_label == "ready" and baseline.maturity_label != "ready":
        improvements.append("Maturity improved to ready.")

    if checksum_changed:
        findings.append("Archive checksum changed; review the listed metric and evidence-chain deltas.")
    else:
        findings.append("Archive checksum is unchanged.")
    if maturity_changed:
        findings.append(f"Maturity changed from {baseline.maturity_label} to {candidate.maturity_label}.")
    if not regressions and not improvements:
        findings.append("No material metadata changes detected between compared archives.")

    if regressions:
        next_actions.append("Review every regression before release sign-off.")
    if source_removed or evidence_removed:
        next_actions.append("Confirm removed source/evidence refs were intentional and documented.")
    if checksum_changed and not regressions:
        next_actions.append("Review checksum change and archive the approved bundle after sign-off.")
    if not regressions:
        next_actions.append("No blocking metadata regression detected; continue normal release readiness review.")

    unchanged_count = sum(
        1
        for key in ("reviewed_source_count", "reviewed_step_count", "blocker_count", "warning_count")
        if metric_deltas[key] == 0
    )
    ready = not regressions and candidate.maturity_label != "blocked"
    maturity = "ready" if ready and checksum_changed else "review_needed" if not regressions else "blocked"
    return AchievementRouteReleaseEvidenceArchiveDiff(
        generated_at=generated_at,
        baseline_archive_id=baseline.archive_id,
        candidate_archive_id=candidate.archive_id,
        ready=ready,
        maturity_label=maturity,
        regression_count=len(regressions),
        improvement_count=len(improvements),
        unchanged_count=unchanged_count,
        source_added=source_added,
        source_removed=source_removed,
        artifact_added=artifact_added,
        artifact_removed=artifact_removed,
        evidence_chain_added=evidence_added,
        evidence_chain_removed=evidence_removed,
        metric_deltas=metric_deltas,
        checksum_changed=checksum_changed,
        maturity_changed=maturity_changed,
        blocker_delta=metric_deltas["blocker_count"],
        warning_delta=metric_deltas["warning_count"],
        reviewed_source_delta=metric_deltas["reviewed_source_count"],
        reviewed_step_delta=metric_deltas["reviewed_step_count"],
        findings=findings,
        regressions=regressions,
        improvements=improvements,
        next_actions=_unique(next_actions),
    )


def render_achievement_route_release_evidence_archive_diff_markdown(
    diff: AchievementRouteReleaseEvidenceArchiveDiff,
) -> str:
    lines = [
        "# Achievement Route Release Evidence Archive Diff",
        "",
        f"- Baseline archive: {diff.baseline_archive_id or 'None'}",
        f"- Candidate archive: {diff.candidate_archive_id or 'None'}",
        f"- Ready: {diff.ready}",
        f"- Maturity: {diff.maturity_label}",
        f"- Regressions: {diff.regression_count}",
        f"- Improvements: {diff.improvement_count}",
        f"- Checksum changed: {diff.checksum_changed}",
        f"- Boundary: {diff.boundary}",
        "",
        "## Metric Deltas",
    ]
    for key, value in diff.metric_deltas.items():
        lines.append(f"- {key}: {value:+d}")
    lines.extend(["", "## Regressions"])
    lines.extend([f"- {item}" for item in diff.regressions] or ["- None"])
    lines.extend(["", "## Improvements"])
    lines.extend([f"- {item}" for item in diff.improvements] or ["- None"])
    lines.extend(["", "## Findings"])
    lines.extend([f"- {item}" for item in diff.findings] or ["- None"])
    lines.extend(["", "## Next Actions"])
    lines.extend([f"- {item}" for item in diff.next_actions] or ["- None"])
    return "\n".join(lines) + "\n"


def render_achievement_route_release_evidence_archive_diff_csv(
    diff: AchievementRouteReleaseEvidenceArchiveDiff,
) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "baseline_archive_id",
            "candidate_archive_id",
            "ready",
            "maturity_label",
            "regression_count",
            "improvement_count",
            "checksum_changed",
            "reviewed_source_delta",
            "reviewed_step_delta",
            "blocker_delta",
            "warning_delta",
        ]
    )
    writer.writerow(
        [
            diff.baseline_archive_id or "",
            diff.candidate_archive_id or "",
            diff.ready,
            diff.maturity_label,
            diff.regression_count,
            diff.improvement_count,
            diff.checksum_changed,
            diff.reviewed_source_delta,
            diff.reviewed_step_delta,
            diff.blocker_delta,
            diff.warning_delta,
        ]
    )
    return buffer.getvalue()


def record_achievement_route_release_signoff(
    request: AchievementRouteReleaseSignoffRequest,
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteReleaseSignoffRecord:
    if not request.confirmed_signoff:
        raise ValueError("confirmed_signoff must be true before recording release sign-off.")
    bundle = build_achievement_route_unified_release_evidence_bundle(source_root, audit_root)
    archive_index = list_achievement_route_release_evidence_archives(audit_root, limit=1)
    latest_archive = archive_index.records[0] if archive_index.records else None
    diff = build_achievement_route_release_evidence_archive_diff(audit_root)
    blockers: list[str] = []
    if latest_archive is None:
        blockers.append("No release evidence archive exists for sign-off.")
    if diff.baseline_archive_id is None or diff.candidate_archive_id is None:
        blockers.append("Release evidence archive diff requires at least two archived records.")
    if diff.regression_count > 0:
        blockers.extend(diff.regressions)
    if bundle.maturity_label == "blocked":
        blockers.append("Unified release evidence bundle is blocked.")
    signed_off_at = datetime.now(UTC)
    status: Literal["signed_off", "blocked"] = "blocked" if blockers else "signed_off"
    record = AchievementRouteReleaseSignoffRecord(
        signoff_id=f"achievement-route-release-signoff:{signed_off_at.strftime('%Y%m%dT%H%M%S%fZ')}:{_safe_identifier(request.reviewer)}",
        signed_off_at=signed_off_at,
        reviewer=request.reviewer,
        status=status,
        bundle_id=bundle.bundle_id,
        archive_id=latest_archive.archive_id if latest_archive else None,
        diff_baseline_archive_id=diff.baseline_archive_id,
        diff_candidate_archive_id=diff.candidate_archive_id,
        bundle_maturity=bundle.maturity_label,
        archive_maturity=latest_archive.maturity_label if latest_archive else None,
        diff_maturity=diff.maturity_label,
        regression_count=diff.regression_count,
        blocker_count=bundle.blocker_count,
        warning_count=bundle.warning_count,
        checksum_changed=diff.checksum_changed,
        notes=request.notes or ["Human reviewer confirmed release evidence sign-off gate."],
        evidence_refs=_unique(
            [
                *request.evidence_refs,
                "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle",
                "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive",
                "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive/diff",
            ]
        ),
        blockers=_unique(blockers),
        next_actions=_unique(
            blockers
            or [
                "Release evidence sign-off recorded; continue external release process manually.",
                "Keep archived evidence and diff exports with the release packet.",
            ]
        ),
    )
    audit_root.mkdir(parents=True, exist_ok=True)
    path = audit_root / "release_signoff_audit.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(record.model_dump_json() + "\n")
    return record


def list_achievement_route_release_signoff_audits(
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    *,
    reviewer: str | None = None,
    status: str | None = None,
    limit: int = 25,
) -> AchievementRouteReleaseSignoffAuditList:
    path = audit_root / "release_signoff_audit.jsonl"
    records: list[AchievementRouteReleaseSignoffRecord] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = AchievementRouteReleaseSignoffRecord.model_validate_json(line)
            except ValidationError:
                continue
            if reviewer and record.reviewer != reviewer:
                continue
            if status and record.status != status:
                continue
            records.append(record)
    records = sorted(records, key=lambda item: item.signed_off_at, reverse=True)[: max(1, min(limit, 200))]
    return AchievementRouteReleaseSignoffAuditList(
        records=records,
        filters={"reviewer": reviewer, "status": status, "limit": limit},
    )


def render_achievement_route_release_signoff_audit_markdown(
    audit: AchievementRouteReleaseSignoffAuditList,
) -> str:
    lines = [
        "# Achievement Route Release Sign-off Audit",
        "",
        f"- Records: {len(audit.records)}",
        f"- Boundary: {audit.boundary}",
        "",
        "## Records",
    ]
    if not audit.records:
        lines.append("- None")
    for record in audit.records:
        lines.extend(
            [
                f"- Sign-off: {record.signoff_id}",
                f"  - Status: {record.status}",
                f"  - Reviewer: {record.reviewer}",
                f"  - Bundle: {record.bundle_id}",
                f"  - Archive: {record.archive_id or 'None'}",
                f"  - Diff: {record.diff_baseline_archive_id or 'None'} -> {record.diff_candidate_archive_id or 'None'}",
                f"  - Regressions: {record.regression_count}",
            ]
        )
    return "\n".join(lines) + "\n"


def render_achievement_route_release_signoff_audit_csv(
    audit: AchievementRouteReleaseSignoffAuditList,
) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "signoff_id",
            "signed_off_at",
            "reviewer",
            "status",
            "bundle_id",
            "archive_id",
            "diff_baseline_archive_id",
            "diff_candidate_archive_id",
            "regression_count",
            "blocker_count",
            "warning_count",
            "checksum_changed",
        ]
    )
    for record in audit.records:
        writer.writerow(
            [
                record.signoff_id,
                record.signed_off_at.isoformat(),
                record.reviewer,
                record.status,
                record.bundle_id,
                record.archive_id or "",
                record.diff_baseline_archive_id or "",
                record.diff_candidate_archive_id or "",
                record.regression_count,
                record.blocker_count,
                record.warning_count,
                record.checksum_changed,
            ]
        )
    return buffer.getvalue()


def build_achievement_route_operator_release_dashboard(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteOperatorReleaseDashboard:
    bundle = build_achievement_route_unified_release_evidence_bundle(source_root, audit_root)
    archive_index = list_achievement_route_release_evidence_archives(audit_root, limit=10)
    diff = build_achievement_route_release_evidence_archive_diff(audit_root)
    signoff_audit = list_achievement_route_release_signoff_audits(audit_root, limit=10)
    latest_signoff = signoff_audit.records[0] if signoff_audit.records else None
    missing_gates: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []

    if not archive_index.records:
        missing_gates.append("release_evidence_archive")
        blockers.append("No release evidence archive has been recorded.")
        next_actions.append("Archive the current release evidence bundle before release sign-off.")
    if diff.baseline_archive_id is None or diff.candidate_archive_id is None:
        missing_gates.append("release_evidence_archive_diff")
        blockers.append("Release evidence archive diff is not available.")
        next_actions.append("Create at least two meaningful release evidence archives before diff review.")
    if not latest_signoff:
        missing_gates.append("release_signoff")
        blockers.append("No release sign-off has been recorded.")
        next_actions.append("Record confirmed release sign-off after archive and diff review.")
    elif latest_signoff.status != "signed_off":
        blockers.append("Latest release sign-off is blocked.")
        next_actions.extend(latest_signoff.next_actions)

    if bundle.maturity_label == "blocked":
        blockers.append("Unified release evidence bundle is blocked.")
    elif bundle.maturity_label == "review_needed":
        warnings.append("Unified release evidence bundle still requires review.")
    if diff.regression_count > 0:
        blockers.extend(diff.regressions)
        next_actions.append("Resolve or explicitly document every archive diff regression.")
    elif diff.maturity_label == "review_needed":
        warnings.append("Release evidence archive diff still requires review.")
    if bundle.warning_count > 0:
        warnings.append(f"Unified release evidence bundle has {bundle.warning_count} warnings.")

    ready = not blockers and latest_signoff is not None and latest_signoff.status == "signed_off"
    maturity = "ready" if ready else "blocked" if blockers else "review_needed"
    if ready:
        next_actions.append("Release dashboard is ready; keep bundle, archive, diff, and sign-off exports with the manual release packet.")

    return AchievementRouteOperatorReleaseDashboard(
        generated_at=datetime.now(UTC),
        ready=ready,
        maturity_label=maturity,
        bundle_id=bundle.bundle_id,
        bundle_maturity=bundle.maturity_label,
        archive_count=archive_index.total_records,
        latest_archive_id=archive_index.latest_archive_id,
        diff_maturity=diff.maturity_label,
        diff_regression_count=diff.regression_count,
        latest_signoff_id=latest_signoff.signoff_id if latest_signoff else None,
        latest_signoff_status=latest_signoff.status if latest_signoff else None,
        latest_signoff_reviewer=latest_signoff.reviewer if latest_signoff else None,
        missing_gates=_unique(missing_gates),
        blockers=_unique(blockers),
        warnings=_unique(warnings),
        next_actions=_unique(next_actions),
        evidence_refs=[
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle",
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive",
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive/diff",
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/signoff-audit",
        ],
        release_evidence_bundle=bundle,
        release_evidence_archive_index=archive_index,
        release_evidence_archive_diff=diff,
        release_signoff_audit=signoff_audit,
    )


def render_achievement_route_operator_release_dashboard_markdown(
    dashboard: AchievementRouteOperatorReleaseDashboard,
) -> str:
    lines = [
        "# Achievement Route Operator Release Dashboard",
        "",
        f"- Ready: {dashboard.ready}",
        f"- Maturity: {dashboard.maturity_label}",
        f"- Bundle: {dashboard.bundle_id}",
        f"- Bundle maturity: {dashboard.bundle_maturity}",
        f"- Archive count: {dashboard.archive_count}",
        f"- Latest archive: {dashboard.latest_archive_id or 'None'}",
        f"- Diff maturity: {dashboard.diff_maturity}",
        f"- Diff regressions: {dashboard.diff_regression_count}",
        f"- Latest sign-off: {dashboard.latest_signoff_status or 'None'}",
        f"- Boundary: {dashboard.boundary}",
        "",
        "## Missing Gates",
    ]
    lines.extend([f"- {item}" for item in dashboard.missing_gates] or ["- None"])
    lines.extend(["", "## Blockers"])
    lines.extend([f"- {item}" for item in dashboard.blockers] or ["- None"])
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {item}" for item in dashboard.warnings] or ["- None"])
    lines.extend(["", "## Next Actions"])
    lines.extend([f"- {item}" for item in dashboard.next_actions] or ["- None"])
    return "\n".join(lines) + "\n"


def render_achievement_route_operator_release_dashboard_csv(
    dashboard: AchievementRouteOperatorReleaseDashboard,
) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "ready",
            "maturity_label",
            "bundle_id",
            "bundle_maturity",
            "archive_count",
            "latest_archive_id",
            "diff_maturity",
            "diff_regression_count",
            "latest_signoff_status",
            "latest_signoff_reviewer",
            "missing_gate_count",
            "blocker_count",
            "warning_count",
        ]
    )
    writer.writerow(
        [
            dashboard.ready,
            dashboard.maturity_label,
            dashboard.bundle_id,
            dashboard.bundle_maturity,
            dashboard.archive_count,
            dashboard.latest_archive_id or "",
            dashboard.diff_maturity,
            dashboard.diff_regression_count,
            dashboard.latest_signoff_status or "",
            dashboard.latest_signoff_reviewer or "",
            len(dashboard.missing_gates),
            len(dashboard.blockers),
            len(dashboard.warnings),
        ]
    )
    return buffer.getvalue()


def build_achievement_route_release_export_packet(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteReleaseExportPacket:
    dashboard = build_achievement_route_operator_release_dashboard(source_root, audit_root)
    generated_at = datetime.now(UTC)
    artifacts = [
        "release_export_packet_manifest.json",
        "release_export_packet.md",
        "release_export_packet.csv",
        "operator_release_dashboard.md",
        "unified_release_evidence_bundle.md",
        "release_evidence_archive.csv",
        "release_evidence_archive_diff.csv",
        "release_signoff_audit.csv",
    ]
    manifest = {
        "packet_schema": "gw2radar.achievement_route_release_export_packet.v1",
        "generated_at": generated_at.isoformat(),
        "ready": dashboard.ready,
        "maturity_label": dashboard.maturity_label,
        "bundle_id": dashboard.bundle_id,
        "latest_archive_id": dashboard.latest_archive_id,
        "latest_signoff_id": dashboard.latest_signoff_id,
        "artifacts": artifacts,
        "source_paths": [
            "docs/knowledge_base/achievement_routes/*.json",
            "data/achievement_route_audit/release_evidence_archive.jsonl",
            "data/achievement_route_audit/release_signoff_audit.jsonl",
        ],
        "api_refs": [
            *dashboard.evidence_refs,
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-dashboard",
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet",
        ],
        "safety_boundaries": [
            "No raw API keys or private account payloads are included.",
            "No source manifests are edited by this packet.",
            "No gameplay, trading, publishing, or deployment action is automated.",
            "This packet is an operator handoff artifact, not a live game-state certificate.",
        ],
    }
    return AchievementRouteReleaseExportPacket(
        packet_id=f"achievement-route-release-export:{generated_at.strftime('%Y%m%dT%H%M%S%fZ')}",
        generated_at=generated_at,
        ready=dashboard.ready,
        maturity_label=dashboard.maturity_label,
        dashboard_schema=dashboard.schema_version,
        bundle_schema=dashboard.release_evidence_bundle.schema_version,
        archive_index_schema=dashboard.release_evidence_archive_index.schema_version,
        diff_schema=dashboard.release_evidence_archive_diff.schema_version,
        signoff_audit_schema=dashboard.release_signoff_audit.schema_version,
        bundle_id=dashboard.bundle_id,
        latest_archive_id=dashboard.latest_archive_id,
        diff_baseline_archive_id=dashboard.release_evidence_archive_diff.baseline_archive_id,
        diff_candidate_archive_id=dashboard.release_evidence_archive_diff.candidate_archive_id,
        latest_signoff_id=dashboard.latest_signoff_id,
        latest_signoff_status=dashboard.latest_signoff_status,
        artifact_count=len(artifacts),
        artifacts=artifacts,
        evidence_refs=_unique(manifest["api_refs"]),
        manifest=manifest,
        dashboard=dashboard,
    )


def render_achievement_route_release_export_packet_markdown(
    packet: AchievementRouteReleaseExportPacket,
) -> str:
    lines = [
        "# Achievement Route Release Export Packet",
        "",
        f"- Packet: {packet.packet_id}",
        f"- Ready: {packet.ready}",
        f"- Maturity: {packet.maturity_label}",
        f"- Bundle: {packet.bundle_id}",
        f"- Latest archive: {packet.latest_archive_id or 'None'}",
        f"- Diff: {packet.diff_baseline_archive_id or 'None'} -> {packet.diff_candidate_archive_id or 'None'}",
        f"- Latest sign-off: {packet.latest_signoff_status or 'None'}",
        f"- Artifacts: {packet.artifact_count}",
        f"- Boundary: {packet.boundary}",
        "",
        "## Artifacts",
    ]
    lines.extend([f"- {item}" for item in packet.artifacts])
    lines.extend(["", "## Dashboard Blockers"])
    lines.extend([f"- {item}" for item in packet.dashboard.blockers] or ["- None"])
    lines.extend(["", "## Dashboard Warnings"])
    lines.extend([f"- {item}" for item in packet.dashboard.warnings] or ["- None"])
    lines.extend(["", "## Evidence Refs"])
    lines.extend([f"- {item}" for item in packet.evidence_refs])
    return "\n".join(lines) + "\n"


def render_achievement_route_release_export_packet_csv(
    packet: AchievementRouteReleaseExportPacket,
) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "packet_id",
            "ready",
            "maturity_label",
            "bundle_id",
            "latest_archive_id",
            "diff_baseline_archive_id",
            "diff_candidate_archive_id",
            "latest_signoff_status",
            "artifact_count",
            "dashboard_blocker_count",
            "dashboard_warning_count",
        ]
    )
    writer.writerow(
        [
            packet.packet_id,
            packet.ready,
            packet.maturity_label,
            packet.bundle_id,
            packet.latest_archive_id or "",
            packet.diff_baseline_archive_id or "",
            packet.diff_candidate_archive_id or "",
            packet.latest_signoff_status or "",
            packet.artifact_count,
            len(packet.dashboard.blockers),
            len(packet.dashboard.warnings),
        ]
    )
    return buffer.getvalue()


def write_achievement_route_release_export_packet_artifacts(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    output_root: Path = ACHIEVEMENT_ROUTE_RELEASE_EXPORT_ROOT,
) -> AchievementRouteReleaseExportArtifactIndex:
    packet = build_achievement_route_release_export_packet(source_root, audit_root)
    safe_packet_id = _safe_identifier(packet.packet_id)
    packet_dir = output_root / safe_packet_id
    packet_dir.mkdir(parents=True, exist_ok=True)
    payloads = {
        "release_export_packet_manifest.json": (json.dumps(packet.manifest, indent=2, sort_keys=True) + "\n", "application/json"),
        "release_export_packet.md": (render_achievement_route_release_export_packet_markdown(packet), "text/markdown"),
        "release_export_packet.csv": (render_achievement_route_release_export_packet_csv(packet), "text/csv"),
    }
    files: list[AchievementRouteReleaseExportArtifactFile] = []
    for filename, (content, media_type) in payloads.items():
        path = packet_dir / filename
        path.write_text(content, encoding="utf-8", newline="\n")
        checksum = hashlib.sha256(content.encode("utf-8")).hexdigest()
        files.append(
            AchievementRouteReleaseExportArtifactFile(
                filename=filename,
                relative_path=(Path(safe_packet_id) / filename).as_posix(),
                media_type=media_type,
                size_bytes=path.stat().st_size,
                checksum_sha256=checksum,
            )
        )
    index = AchievementRouteReleaseExportArtifactIndex(
        packet_id=packet.packet_id,
        packet_dir=packet_dir.as_posix(),
        generated_at=datetime.now(UTC),
        file_count=len(files),
        files=files,
    )
    (packet_dir / "artifact_index.json").write_text(index.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")
    return index


def list_achievement_route_release_export_artifacts(
    output_root: Path = ACHIEVEMENT_ROUTE_RELEASE_EXPORT_ROOT,
    *,
    limit: int = 25,
) -> AchievementRouteReleaseExportArtifactIndex:
    indexes: list[AchievementRouteReleaseExportArtifactIndex] = []
    if output_root.exists():
        for path in output_root.glob("*/artifact_index.json"):
            try:
                indexes.append(AchievementRouteReleaseExportArtifactIndex.model_validate_json(path.read_text(encoding="utf-8")))
            except ValidationError:
                continue
    indexes = sorted(indexes, key=lambda item: item.generated_at, reverse=True)[: max(1, min(limit, 200))]
    files = [file for index in indexes for file in index.files]
    latest = indexes[0] if indexes else None
    return AchievementRouteReleaseExportArtifactIndex(
        packet_id=latest.packet_id if latest else None,
        packet_dir=latest.packet_dir if latest else None,
        generated_at=datetime.now(UTC),
        file_count=len(files),
        files=files,
    )


def resolve_achievement_route_release_export_artifact_path(
    relative_path: str,
    output_root: Path = ACHIEVEMENT_ROUTE_RELEASE_EXPORT_ROOT,
) -> Path | None:
    root = output_root.resolve()
    candidate = (output_root / relative_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate


def build_achievement_route_release_export_bundle(
    output_root: Path = ACHIEVEMENT_ROUTE_RELEASE_EXPORT_ROOT,
) -> tuple[AchievementRouteReleaseExportBundleManifest, bytes]:
    index = list_achievement_route_release_export_artifacts(output_root, limit=1)
    if not index.files:
        raise ValueError("No release export artifacts are available to bundle")
    packet_dir_name = index.files[0].relative_path.split("/", 1)[0]
    allowed_filenames = {
        "artifact_index.json",
        "release_export_packet_manifest.json",
        "release_export_packet.md",
        "release_export_packet.csv",
    }
    source_files: list[tuple[str, Path, str]] = []
    for file in index.files:
        if file.filename not in allowed_filenames:
            continue
        path = resolve_achievement_route_release_export_artifact_path(file.relative_path, output_root)
        if path is not None:
            source_files.append((file.relative_path, path, file.media_type))
    artifact_index_relative = f"{packet_dir_name}/artifact_index.json"
    artifact_index_path = resolve_achievement_route_release_export_artifact_path(artifact_index_relative, output_root)
    if artifact_index_path is not None:
        source_files.append((artifact_index_relative, artifact_index_path, "application/json"))

    included_files: list[AchievementRouteReleaseExportArtifactFile] = []
    buffer = BytesIO()
    with ZipFile(buffer, mode="w", compression=ZIP_DEFLATED) as archive:
        for relative_path, path, media_type in sorted(source_files, key=lambda item: item[0]):
            filename = Path(relative_path).name
            if filename not in allowed_filenames:
                continue
            content = path.read_bytes()
            archive_path = f"achievement_route_release_export/{filename}"
            info = ZipInfo(archive_path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)
            included_files.append(
                AchievementRouteReleaseExportArtifactFile(
                    filename=filename,
                    relative_path=archive_path,
                    media_type=media_type,
                    size_bytes=len(content),
                    checksum_sha256=hashlib.sha256(content).hexdigest(),
                )
            )
    bundle_bytes = buffer.getvalue()
    safe_packet_id = _safe_identifier(index.packet_id or "latest")
    filename = f"{safe_packet_id}_release_export_bundle.zip"
    checksum = hashlib.sha256(bundle_bytes).hexdigest()
    manifest = AchievementRouteReleaseExportBundleManifest(
        bundle_id=f"achievement-route-release-export-bundle:{checksum[:16]}",
        packet_id=index.packet_id,
        generated_at=datetime.now(UTC),
        filename=filename,
        file_count=len(included_files),
        included_files=included_files,
        checksum_sha256=checksum,
        size_bytes=len(bundle_bytes),
    )
    return manifest, bundle_bytes


def verify_achievement_route_release_export_bundle(
    bundle_bytes: bytes,
    *,
    expected_checksum_sha256: str | None = None,
) -> AchievementRouteReleaseExportBundleVerification:
    checksum = hashlib.sha256(bundle_bytes).hexdigest()
    blockers: list[str] = []
    warnings: list[str] = []
    allowed_names = {
        "achievement_route_release_export/artifact_index.json",
        "achievement_route_release_export/release_export_packet_manifest.json",
        "achievement_route_release_export/release_export_packet.md",
        "achievement_route_release_export/release_export_packet.csv",
    }
    verified_files: list[str] = []
    if expected_checksum_sha256 and expected_checksum_sha256 != checksum:
        blockers.append("bundle checksum does not match the expected SHA-256 value")
    try:
        with ZipFile(BytesIO(bundle_bytes), mode="r") as archive:
            names = sorted(archive.namelist())
            verified_files = names
            for name in names:
                path = Path(name)
                if path.is_absolute() or ".." in path.parts:
                    blockers.append(f"bundle contains unsafe path: {name}")
            extra_names = sorted(set(names) - allowed_names)
            missing_names = sorted(allowed_names - set(names))
            if extra_names:
                blockers.append("bundle contains non-whitelisted files: " + ", ".join(extra_names))
            if missing_names:
                blockers.append("bundle is missing required files: " + ", ".join(missing_names))
            for name in names:
                content = archive.read(name)
                if b"secret-key" in content.lower():
                    blockers.append(f"bundle file contains prohibited secret marker: {name}")
            if "achievement_route_release_export/artifact_index.json" in names:
                try:
                    AchievementRouteReleaseExportArtifactIndex.model_validate_json(
                        archive.read("achievement_route_release_export/artifact_index.json").decode("utf-8")
                    )
                except (UnicodeDecodeError, ValidationError, ValueError) as exc:
                    blockers.append(f"artifact index validation failed: {exc}")
            if "achievement_route_release_export/release_export_packet_manifest.json" in names:
                try:
                    packet_manifest = json.loads(
                        archive.read("achievement_route_release_export/release_export_packet_manifest.json").decode("utf-8")
                    )
                    if packet_manifest.get("packet_schema") != "gw2radar.achievement_route_release_export_packet.v1":
                        blockers.append("release export packet manifest schema mismatch")
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    blockers.append(f"release export packet manifest validation failed: {exc}")
            if "achievement_route_release_export/release_export_packet.md" in names:
                try:
                    markdown = archive.read("achievement_route_release_export/release_export_packet.md").decode("utf-8")
                    if "Achievement Route Release Export Packet" not in markdown:
                        blockers.append("release export packet Markdown title is missing")
                    if "guaranteed" in markdown.lower():
                        blockers.append("release export packet Markdown contains prohibited guarantee wording")
                except UnicodeDecodeError as exc:
                    blockers.append(f"release export packet Markdown is not UTF-8: {exc}")
            if "achievement_route_release_export/release_export_packet.csv" in names:
                try:
                    csv_text = archive.read("achievement_route_release_export/release_export_packet.csv").decode("utf-8")
                    if "packet_id,ready,maturity_label" not in csv_text:
                        blockers.append("release export packet CSV header mismatch")
                except UnicodeDecodeError as exc:
                    blockers.append(f"release export packet CSV is not UTF-8: {exc}")
    except Exception as exc:
        blockers.append(f"bundle zip could not be read: {exc}")
    if len(bundle_bytes) > 5_000_000:
        warnings.append("bundle is larger than the MVP verification target of 5 MB")
    return AchievementRouteReleaseExportBundleVerification(
        ready=not blockers,
        verified_at=datetime.now(UTC),
        checksum_sha256=checksum,
        size_bytes=len(bundle_bytes),
        file_count=len(verified_files),
        verified_files=verified_files,
        blockers=blockers,
        warnings=warnings,
    )


def record_achievement_route_release_export_bundle_verification_audit(
    request: AchievementRouteReleaseExportBundleVerificationAuditRequest,
    bundle_bytes: bytes | None = None,
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    output_root: Path = ACHIEVEMENT_ROUTE_RELEASE_EXPORT_ROOT,
) -> AchievementRouteReleaseExportBundleVerificationAuditRecord:
    expected_checksum = request.expected_checksum_sha256
    if bundle_bytes is None or len(bundle_bytes) == 0:
        index = list_achievement_route_release_export_artifacts(output_root, limit=1)
        if not index.files:
            write_achievement_route_release_export_packet_artifacts(source_root, audit_root, output_root)
        manifest, bundle_bytes = build_achievement_route_release_export_bundle(output_root)
        expected_checksum = expected_checksum or manifest.checksum_sha256
    verification = verify_achievement_route_release_export_bundle(
        bundle_bytes,
        expected_checksum_sha256=expected_checksum,
    )
    verified_at = datetime.now(UTC)
    record = AchievementRouteReleaseExportBundleVerificationAuditRecord(
        audit_id=f"achievement-route-release-bundle-verification:{verified_at.strftime('%Y%m%dT%H%M%S%fZ')}:{_safe_identifier(request.reviewer)}",
        verified_at=verified_at,
        reviewer=request.reviewer,
        ready=verification.ready,
        checksum_sha256=verification.checksum_sha256,
        size_bytes=verification.size_bytes,
        file_count=verification.file_count,
        blocker_count=len(verification.blockers),
        warning_count=len(verification.warnings),
        verified_files=verification.verified_files,
        blockers=verification.blockers,
        warnings=verification.warnings,
        notes=request.notes or ["Release bundle verification audit recorded by reviewer."],
        evidence_refs=_unique(
            [
                *request.evidence_refs,
                "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle",
                "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verify",
            ]
        ),
    )
    audit_root.mkdir(parents=True, exist_ok=True)
    path = audit_root / "release_bundle_verification_audit.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(record.model_dump_json() + "\n")
    return record


def list_achievement_route_release_export_bundle_verification_audits(
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    *,
    reviewer: str | None = None,
    ready: bool | None = None,
    limit: int = 25,
) -> AchievementRouteReleaseExportBundleVerificationAuditList:
    path = audit_root / "release_bundle_verification_audit.jsonl"
    records: list[AchievementRouteReleaseExportBundleVerificationAuditRecord] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = AchievementRouteReleaseExportBundleVerificationAuditRecord.model_validate_json(line)
            except ValidationError:
                continue
            if reviewer and record.reviewer != reviewer:
                continue
            if ready is not None and record.ready is not ready:
                continue
            records.append(record)
    records = sorted(records, key=lambda item: item.verified_at, reverse=True)[: max(1, min(limit, 200))]
    return AchievementRouteReleaseExportBundleVerificationAuditList(
        records=records,
        filters={"reviewer": reviewer, "ready": ready, "limit": limit},
    )


def render_achievement_route_release_export_bundle_verification_audit_markdown(
    audit: AchievementRouteReleaseExportBundleVerificationAuditList,
) -> str:
    lines = [
        "# Achievement Route Release Bundle Verification Audit",
        "",
        f"- Records: {len(audit.records)}",
        f"- Boundary: {audit.boundary}",
        "",
        "## Records",
    ]
    if not audit.records:
        lines.append("- None")
    for record in audit.records:
        lines.extend(
            [
                f"- Audit: {record.audit_id}",
                f"  - Reviewer: {record.reviewer}",
                f"  - Ready: {record.ready}",
                f"  - Checksum: {record.checksum_sha256}",
                f"  - Files: {record.file_count}",
                f"  - Blockers: {record.blocker_count}",
                f"  - Warnings: {record.warning_count}",
            ]
        )
    return "\n".join(lines) + "\n"


def render_achievement_route_release_export_bundle_verification_audit_csv(
    audit: AchievementRouteReleaseExportBundleVerificationAuditList,
) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "audit_id",
            "verified_at",
            "reviewer",
            "ready",
            "checksum_sha256",
            "size_bytes",
            "file_count",
            "blocker_count",
            "warning_count",
        ]
    )
    for record in audit.records:
        writer.writerow(
            [
                record.audit_id,
                record.verified_at.isoformat(),
                record.reviewer,
                record.ready,
                record.checksum_sha256,
                record.size_bytes,
                record.file_count,
                record.blocker_count,
                record.warning_count,
            ]
        )
    return buffer.getvalue()


def build_achievement_route_operator_handoff_checklist(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    output_root: Path = ACHIEVEMENT_ROUTE_RELEASE_EXPORT_ROOT,
) -> AchievementRouteOperatorHandoffChecklist:
    packet = build_achievement_route_release_export_packet(source_root, audit_root)
    artifact_index = list_achievement_route_release_export_artifacts(output_root, limit=1)
    if not artifact_index.files:
        artifact_index = write_achievement_route_release_export_packet_artifacts(source_root, audit_root, output_root)

    bundle_manifest: AchievementRouteReleaseExportBundleManifest | None = None
    bundle_verification: AchievementRouteReleaseExportBundleVerification | None = None
    blockers: list[str] = []
    warnings: list[str] = []
    try:
        bundle_manifest, bundle_bytes = build_achievement_route_release_export_bundle(output_root)
        bundle_verification = verify_achievement_route_release_export_bundle(
            bundle_bytes,
            expected_checksum_sha256=bundle_manifest.checksum_sha256,
        )
    except ValueError as exc:
        blockers.append(str(exc))

    verification_audit = list_achievement_route_release_export_bundle_verification_audits(audit_root, limit=1)
    latest_audit = verification_audit.records[0] if verification_audit.records else None
    missing_gates: list[str] = []
    if packet.manifest.get("packet_schema") != "gw2radar.achievement_route_release_export_packet.v1":
        missing_gates.append("release export packet manifest schema")
    if artifact_index.file_count < 3:
        missing_gates.append("release packet artifact files")
    if bundle_manifest is None or bundle_manifest.file_count < 4:
        missing_gates.append("release packet zip bundle")
    if bundle_verification is None or not bundle_verification.ready:
        missing_gates.append("release packet bundle verification")
    if latest_audit is None:
        missing_gates.append("release packet bundle verification audit")
    elif not latest_audit.ready:
        missing_gates.append("latest release packet bundle verification audit ready state")

    if bundle_verification and bundle_verification.blockers:
        blockers.extend(bundle_verification.blockers)
    if latest_audit and latest_audit.blockers:
        blockers.extend(latest_audit.blockers)
    if bundle_verification and bundle_verification.warnings:
        warnings.extend(bundle_verification.warnings)
    if latest_audit and latest_audit.warnings:
        warnings.extend(latest_audit.warnings)

    ready = not missing_gates and not blockers
    maturity_label: Literal["blocked", "review_needed", "ready"]
    if blockers:
        maturity_label = "blocked"
    elif missing_gates or warnings:
        maturity_label = "review_needed"
    else:
        maturity_label = "ready"
    checklist_items = [
        "Release export packet manifest generated.",
        "Release packet artifact files written and indexed.",
        "Release packet zip bundle generated from whitelist files.",
        "Release packet zip bundle verified without executing content.",
        "Release packet verification audit recorded as metadata only.",
    ]
    next_actions = (
        [
            "Resolve missing handoff gates before external release handoff.",
            "Re-run bundle verification and record audit after blockers are fixed.",
        ]
        if not ready
        else [
            "Attach release packet bundle, verification audit export, and checklist to the manual operator handoff.",
            "Keep external publication and deployment steps manual until a separate release process is approved.",
        ]
    )
    return AchievementRouteOperatorHandoffChecklist(
        generated_at=datetime.now(UTC),
        ready=ready,
        maturity_label=maturity_label,
        packet_id=packet.packet_id,
        packet_artifact_count=artifact_index.file_count,
        bundle_checksum_sha256=bundle_manifest.checksum_sha256 if bundle_manifest else None,
        bundle_file_count=bundle_manifest.file_count if bundle_manifest else 0,
        verification_ready=bundle_verification.ready if bundle_verification else False,
        verification_audit_count=len(verification_audit.records),
        latest_verification_audit_id=latest_audit.audit_id if latest_audit else None,
        checklist_items=checklist_items,
        missing_gates=_unique(missing_gates),
        blockers=_unique(blockers),
        warnings=_unique(warnings),
        next_actions=next_actions,
        evidence_refs=_unique(
            [
                "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet",
                "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts",
                "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle",
                "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verify",
                "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verification-audit",
            ]
        ),
    )


def render_achievement_route_operator_handoff_checklist_markdown(
    checklist: AchievementRouteOperatorHandoffChecklist,
) -> str:
    lines = [
        "# Achievement Route Operator Handoff Checklist",
        "",
        f"- Ready: {checklist.ready}",
        f"- Maturity: {checklist.maturity_label}",
        f"- Packet: {checklist.packet_id or 'None'}",
        f"- Packet artifact files: {checklist.packet_artifact_count}",
        f"- Bundle files: {checklist.bundle_file_count}",
        f"- Bundle checksum: {checklist.bundle_checksum_sha256 or 'None'}",
        f"- Verification ready: {checklist.verification_ready}",
        f"- Verification audit records: {checklist.verification_audit_count}",
        f"- Boundary: {checklist.boundary}",
        "",
        "## Checklist",
    ]
    lines.extend(f"- {item}" for item in checklist.checklist_items)
    lines.extend(["", "## Missing Gates"])
    lines.extend(f"- {item}" for item in checklist.missing_gates) if checklist.missing_gates else lines.append("- None")
    lines.extend(["", "## Blockers"])
    lines.extend(f"- {item}" for item in checklist.blockers) if checklist.blockers else lines.append("- None")
    lines.extend(["", "## Next Actions"])
    lines.extend(f"- {item}" for item in checklist.next_actions)
    return "\n".join(lines) + "\n"


def render_achievement_route_operator_handoff_checklist_csv(
    checklist: AchievementRouteOperatorHandoffChecklist,
) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "ready",
            "maturity_label",
            "packet_id",
            "packet_artifact_count",
            "bundle_file_count",
            "verification_ready",
            "verification_audit_count",
            "missing_gate_count",
            "blocker_count",
            "warning_count",
        ]
    )
    writer.writerow(
        [
            checklist.ready,
            checklist.maturity_label,
            checklist.packet_id,
            checklist.packet_artifact_count,
            checklist.bundle_file_count,
            checklist.verification_ready,
            checklist.verification_audit_count,
            len(checklist.missing_gates),
            len(checklist.blockers),
            len(checklist.warnings),
        ]
    )
    return buffer.getvalue()


def build_achievement_route_backfill_candidates(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteBackfillCandidateExport:
    queue = build_achievement_route_remediation_queue(source_root, audit_root)
    readiness = build_achievement_route_remediation_readiness(source_root, audit_root)
    unresolved_ids = set(readiness.unresolved_item_ids)
    candidates: list[AchievementRouteBackfillCandidate] = []
    excluded: list[str] = []
    for item in queue.items:
        if item.item_id not in unresolved_ids:
            excluded.append(item.item_id)
            continue
        candidates.append(_route_backfill_candidate(item))
    return AchievementRouteBackfillCandidateExport(
        candidate_count=len(candidates),
        candidates=candidates,
        excluded_item_ids=_unique(excluded),
    )


def render_achievement_route_backfill_candidates_markdown(export: AchievementRouteBackfillCandidateExport) -> str:
    lines = [
        "# Achievement Route Backfill Candidates",
        "",
        f"- Candidates: {export.candidate_count}",
        f"- Excluded resolved items: {len(export.excluded_item_ids)}",
        f"- Boundary: {export.boundary}",
        "",
        "## Candidates",
    ]
    for candidate in export.candidates:
        lines.extend(
            [
                f"### {candidate.priority} {candidate.title}",
                f"- Candidate: {candidate.candidate_id}",
                f"- Item: {candidate.item_id}",
                f"- Type: {candidate.remediation_type}",
                f"- Source: {candidate.source_id or 'n/a'}",
                f"- Step: {candidate.step_id or 'n/a'}",
                f"- Rationale: {candidate.rationale}",
                f"- Suggested fields: {json.dumps(candidate.suggested_fields, sort_keys=True)}",
                f"- Required review: {', '.join(candidate.required_review)}",
                f"- Evidence: {', '.join(candidate.evidence_refs) if candidate.evidence_refs else 'pending'}",
                "",
            ]
        )
    if not export.candidates:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def render_achievement_route_backfill_candidates_csv(export: AchievementRouteBackfillCandidateExport) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "candidate_id",
            "item_id",
            "priority",
            "remediation_type",
            "source_id",
            "step_id",
            "title",
            "suggested_fields",
            "required_review",
            "evidence_refs",
        ]
    )
    for candidate in export.candidates:
        writer.writerow(
            [
                candidate.candidate_id,
                candidate.item_id,
                candidate.priority,
                candidate.remediation_type,
                candidate.source_id or "",
                candidate.step_id or "",
                candidate.title,
                json.dumps(candidate.suggested_fields, sort_keys=True),
                ";".join(candidate.required_review),
                ";".join(candidate.evidence_refs),
            ]
        )
    return buffer.getvalue()


def record_achievement_route_backfill_candidate_review(
    request: AchievementRouteBackfillCandidateReviewRequest,
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteBackfillCandidateReviewRecord:
    if not request.confirmed_manual_review:
        raise ValueError("Backfill candidate review requires confirmed_manual_review=true.")
    export = build_achievement_route_backfill_candidates(source_root, audit_root)
    candidate_by_id = {candidate.candidate_id: candidate for candidate in export.candidates}
    candidate = candidate_by_id.get(request.candidate_id)
    if candidate is None:
        raise ValueError(f"Backfill candidate {request.candidate_id} is not present in the current review queue.")
    record = AchievementRouteBackfillCandidateReviewRecord(
        event_id=f"route-backfill-candidate-review:{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
        candidate_id=request.candidate_id,
        item_id=candidate.item_id,
        status=request.status,
        occurred_at=datetime.now(UTC),
        reviewer=request.reviewer,
        notes=_unique([note.strip() for note in request.notes if note.strip()]),
        evidence_refs=_unique([*candidate.evidence_refs, *[ref.strip() for ref in request.evidence_refs if ref.strip()]]),
        source_id=candidate.source_id,
        step_id=candidate.step_id,
        remediation_type=candidate.remediation_type,
        priority=candidate.priority,
    )
    audit_root.mkdir(parents=True, exist_ok=True)
    path = audit_root / "backfill_candidate_review_audit.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(record.model_dump_json() + "\n")
    return record


def list_achievement_route_backfill_candidate_review_audits(
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    *,
    reviewer: str | None = None,
    status: RouteRemediationReviewStatus | None = None,
    candidate_id: str | None = None,
    limit: int = 25,
) -> AchievementRouteBackfillCandidateReviewAuditList:
    path = audit_root / "backfill_candidate_review_audit.jsonl"
    records: list[AchievementRouteBackfillCandidateReviewRecord] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = AchievementRouteBackfillCandidateReviewRecord.model_validate_json(line)
            except ValidationError:
                continue
            if reviewer and record.reviewer != reviewer:
                continue
            if status and record.status != status:
                continue
            if candidate_id and record.candidate_id != candidate_id:
                continue
            records.append(record)
    records = sorted(records, key=lambda item: item.occurred_at, reverse=True)[: max(1, min(limit, 200))]
    return AchievementRouteBackfillCandidateReviewAuditList(
        records=records,
        filters={"reviewer": reviewer, "status": status, "candidate_id": candidate_id, "limit": limit},
    )


def render_achievement_route_backfill_candidate_review_audit_markdown(
    audit_list: AchievementRouteBackfillCandidateReviewAuditList,
) -> str:
    lines = [
        "# Achievement Route Backfill Candidate Review Audit",
        "",
        f"- Records: {len(audit_list.records)}",
        f"- Boundary: {audit_list.boundary}",
        "",
        "| Occurred At | Reviewer | Status | Priority | Type | Candidate | Item | Source | Step |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for record in audit_list.records:
        lines.append(
            "| "
            + " | ".join(
                [
                    record.occurred_at.isoformat(),
                    record.reviewer,
                    record.status,
                    record.priority or "n/a",
                    record.remediation_type or "n/a",
                    record.candidate_id,
                    record.item_id,
                    record.source_id or "n/a",
                    record.step_id or "n/a",
                ]
            )
            + " |"
        )
    if not audit_list.records:
        lines.append("| none | none | none | none | none | none | none | none | none |")
    return "\n".join(lines) + "\n"


def render_achievement_route_backfill_candidate_review_audit_csv(
    audit_list: AchievementRouteBackfillCandidateReviewAuditList,
) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "event_id",
            "occurred_at",
            "reviewer",
            "status",
            "priority",
            "remediation_type",
            "candidate_id",
            "item_id",
            "source_id",
            "step_id",
            "notes",
            "evidence_refs",
        ]
    )
    for record in audit_list.records:
        writer.writerow(
            [
                record.event_id,
                record.occurred_at.isoformat(),
                record.reviewer,
                record.status,
                record.priority or "",
                record.remediation_type or "",
                record.candidate_id,
                record.item_id,
                record.source_id or "",
                record.step_id or "",
                ";".join(record.notes),
                ";".join(record.evidence_refs),
            ]
        )
    return buffer.getvalue()


def build_achievement_route_backfill_candidate_readiness(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteBackfillCandidateReadiness:
    export = build_achievement_route_backfill_candidates(source_root, audit_root)
    audit = list_achievement_route_backfill_candidate_review_audits(audit_root, limit=200)
    latest_by_candidate: dict[str, AchievementRouteBackfillCandidateReviewRecord] = {}
    for record in sorted(audit.records, key=lambda item: item.occurred_at):
        latest_by_candidate[record.candidate_id] = record

    unresolved_candidate_ids: list[str] = []
    deferred_candidate_ids: list[str] = []
    resolved_without_extra_evidence: list[str] = []
    resolved_count = 0
    acknowledged_count = 0
    deferred_count = 0
    reviewed_count = 0

    for candidate in export.candidates:
        record = latest_by_candidate.get(candidate.candidate_id)
        if record is None:
            unresolved_candidate_ids.append(candidate.candidate_id)
            continue
        reviewed_count += 1
        if record.status == "resolved":
            resolved_count += 1
            extra_evidence = [ref for ref in record.evidence_refs if ref not in candidate.evidence_refs]
            if not extra_evidence:
                resolved_without_extra_evidence.append(candidate.candidate_id)
        elif record.status == "acknowledged":
            acknowledged_count += 1
            unresolved_candidate_ids.append(candidate.candidate_id)
        elif record.status == "deferred":
            deferred_count += 1
            deferred_candidate_ids.append(candidate.candidate_id)
            unresolved_candidate_ids.append(candidate.candidate_id)

    open_p0 = sum(1 for candidate in export.candidates if candidate.priority == "P0" and candidate.candidate_id in unresolved_candidate_ids)
    open_p1 = sum(1 for candidate in export.candidates if candidate.priority == "P1" and candidate.candidate_id in unresolved_candidate_ids)
    open_p2 = sum(1 for candidate in export.candidates if candidate.priority == "P2" and candidate.candidate_id in unresolved_candidate_ids)
    blockers: list[str] = []
    warnings: list[str] = []
    next_steps: list[str] = []
    if open_p0:
        blockers.append(f"{open_p0} P0 backfill candidates remain unresolved.")
        next_steps.append("Resolve P0 source-edit candidates before release packet approval.")
    if open_p1:
        blockers.append(f"{open_p1} P1 backfill candidates remain unresolved.")
        next_steps.append("Resolve or explicitly defer P1 backfill candidates with reviewer notes.")
    if deferred_candidate_ids:
        warnings.append("Some backfill candidates are deferred and require release-owner acceptance.")
        next_steps.append("Review deferred candidate risk before go/no-go.")
    if resolved_without_extra_evidence:
        warnings.append("Some resolved backfill candidates did not add evidence beyond draft candidate evidence refs.")
        next_steps.append("Attach official API/wiki or source manifest evidence to resolved candidate reviews.")
    if not export.candidates:
        next_steps.append("No backfill candidates are open; continue release packet and patch freshness checks.")

    score = 100.0
    score -= open_p0 * 35
    score -= open_p1 * 20
    score -= min(open_p2 * 5, 20)
    score -= min(len(deferred_candidate_ids) * 10, 30)
    score -= min(len(resolved_without_extra_evidence) * 5, 20)
    score = max(0.0, min(100.0, score))
    ready = not blockers and not deferred_candidate_ids and not resolved_without_extra_evidence
    if export.candidates and reviewed_count < len(export.candidates):
        ready = False
    maturity = "ready" if ready else "blocked" if blockers else "review_needed"
    if not next_steps and ready:
        next_steps.append("Backfill candidate readiness is ready; continue release packet and patch freshness review.")

    return AchievementRouteBackfillCandidateReadiness(
        ready=ready,
        maturity_label=maturity,
        readiness_score=round(score, 1),
        candidate_count=len(export.candidates),
        reviewed_candidate_count=reviewed_count,
        resolved_count=resolved_count,
        acknowledged_count=acknowledged_count,
        deferred_count=deferred_count,
        open_candidate_count=len(_unique(unresolved_candidate_ids)),
        unresolved_candidate_ids=_unique(unresolved_candidate_ids),
        deferred_candidate_ids=_unique(deferred_candidate_ids),
        resolved_without_extra_evidence_candidate_ids=_unique(resolved_without_extra_evidence),
        blockers=blockers,
        warnings=warnings,
        next_steps=_unique(next_steps),
        evidence_chain=[
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates",
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/review-audit",
            "data/achievement_route_audit/backfill_candidate_review_audit.jsonl",
        ],
    )


def render_achievement_route_backfill_candidate_readiness_markdown(
    readiness: AchievementRouteBackfillCandidateReadiness,
) -> str:
    lines = [
        "# Achievement Route Backfill Candidate Readiness",
        "",
        f"- Ready: {readiness.ready}",
        f"- Maturity: {readiness.maturity_label}",
        f"- Score: {readiness.readiness_score}/100",
        f"- Candidates: {readiness.candidate_count}",
        f"- Reviewed candidates: {readiness.reviewed_candidate_count}",
        f"- Open candidates: {readiness.open_candidate_count}",
        f"- Resolved/Acknowledged/Deferred: {readiness.resolved_count}/{readiness.acknowledged_count}/{readiness.deferred_count}",
        f"- Boundary: {readiness.boundary}",
        "",
        "## Blockers",
    ]
    lines.extend([f"- {item}" for item in readiness.blockers] or ["- None"])
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {item}" for item in readiness.warnings] or ["- None"])
    lines.extend(["", "## Next Steps"])
    lines.extend([f"- {item}" for item in readiness.next_steps] or ["- None"])
    lines.extend(["", "## Evidence Chain"])
    lines.extend([f"- {item}" for item in readiness.evidence_chain])
    return "\n".join(lines) + "\n"


def render_achievement_route_backfill_candidate_readiness_csv(
    readiness: AchievementRouteBackfillCandidateReadiness,
) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "ready",
            "maturity_label",
            "readiness_score",
            "candidate_count",
            "reviewed_candidate_count",
            "open_candidate_count",
            "resolved_count",
            "acknowledged_count",
            "deferred_count",
            "unresolved_candidate_ids",
            "deferred_candidate_ids",
            "blockers",
            "warnings",
            "next_steps",
        ]
    )
    writer.writerow(
        [
            readiness.ready,
            readiness.maturity_label,
            readiness.readiness_score,
            readiness.candidate_count,
            readiness.reviewed_candidate_count,
            readiness.open_candidate_count,
            readiness.resolved_count,
            readiness.acknowledged_count,
            readiness.deferred_count,
            ";".join(readiness.unresolved_candidate_ids),
            ";".join(readiness.deferred_candidate_ids),
            ";".join(readiness.blockers),
            ";".join(readiness.warnings),
            ";".join(readiness.next_steps),
        ]
    )
    return buffer.getvalue()


def build_achievement_route_source_edit_patch_draft(
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteSourceEditPatchDraftExport:
    export = build_achievement_route_backfill_candidates(source_root, audit_root)
    audit = list_achievement_route_backfill_candidate_review_audits(audit_root, limit=200)
    latest_by_candidate: dict[str, AchievementRouteBackfillCandidateReviewRecord] = {}
    for record in sorted(audit.records, key=lambda item: item.occurred_at):
        latest_by_candidate[record.candidate_id] = record

    manifests = [
        manifest
        for manifest in load_achievement_route_source_manifests(source_root)
        if isinstance(manifest, AchievementRouteSourceManifest) and manifest.source_status == "reviewed"
    ]
    manifest_by_source = {manifest.source_id: manifest for manifest in manifests}
    drafts: list[AchievementRouteSourceEditPatchDraft] = []
    excluded: list[str] = []
    warnings: list[str] = []

    for candidate in export.candidates:
        review = latest_by_candidate.get(candidate.candidate_id)
        if review is None or review.status != "resolved":
            excluded.append(candidate.candidate_id)
            continue
        manifest = manifest_by_source.get(candidate.source_id or "")
        if candidate.source_id and manifest is None:
            warnings.append(f"Candidate {candidate.candidate_id} references source {candidate.source_id}, but no reviewed manifest was loaded.")
        operations = _route_source_edit_patch_operations(candidate, manifest)
        if not operations:
            warnings.append(f"Candidate {candidate.candidate_id} did not produce concrete patch operations and needs manual source review.")
            excluded.append(candidate.candidate_id)
            continue
        manifest_path = str(_reviewed_manifest_path(source_root, candidate.source_id)) if candidate.source_id else None
        drafts.append(
            AchievementRouteSourceEditPatchDraft(
                draft_id=f"source-edit-patch:{_slug(candidate.candidate_id)}",
                candidate_id=candidate.candidate_id,
                item_id=candidate.item_id,
                priority=candidate.priority,
                remediation_type=candidate.remediation_type,
                title=candidate.title,
                reviewer=review.reviewer,
                reviewed_at=review.occurred_at,
                source_id=candidate.source_id,
                step_id=candidate.step_id,
                source_manifest_path=manifest_path,
                operations=operations,
                evidence_refs=_unique([*candidate.evidence_refs, *review.evidence_refs]),
            )
        )

    blockers: list[str] = []
    next_steps: list[str] = []
    unresolved_count = len(export.candidates) - len(drafts)
    if unresolved_count:
        blockers.append(f"{unresolved_count} backfill candidates are not resolved and cannot become patch drafts.")
        next_steps.append("Resolve candidate review gates before generating source edit patch drafts for every open remediation item.")
    if drafts:
        next_steps.append("Review generated patch operations, apply source manifest edits manually, then re-run source quality and promotion readiness.")
    else:
        next_steps.append("No source edit patch drafts are ready; continue candidate review before editing source manifests.")

    operation_count = sum(len(draft.operations) for draft in drafts)
    return AchievementRouteSourceEditPatchDraftExport(
        generated_at=datetime.now(UTC),
        draft_count=len(drafts),
        operation_count=operation_count,
        drafts=drafts,
        excluded_candidate_ids=_unique(excluded),
        blockers=blockers,
        warnings=_unique(warnings),
        next_steps=_unique(next_steps),
        evidence_chain=[
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates",
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/review-audit",
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft",
        ],
    )


def render_achievement_route_source_edit_patch_draft_markdown(
    export: AchievementRouteSourceEditPatchDraftExport,
) -> str:
    lines = [
        "# Achievement Route Source Edit Patch Draft",
        "",
        f"- Drafts: {export.draft_count}",
        f"- Operations: {export.operation_count}",
        f"- Excluded candidates: {len(export.excluded_candidate_ids)}",
        f"- Boundary: {export.boundary}",
        "",
        "## Drafts",
    ]
    for draft in export.drafts:
        lines.extend(
            [
                f"### {draft.priority} {draft.title}",
                f"- Draft: {draft.draft_id}",
                f"- Candidate: {draft.candidate_id}",
                f"- Type: {draft.remediation_type}",
                f"- Reviewer: {draft.reviewer}",
                f"- Source: {draft.source_id or 'n/a'}",
                f"- Step: {draft.step_id or 'n/a'}",
                f"- Manifest path: {draft.source_manifest_path or 'n/a'}",
                f"- Boundary: {draft.safety_boundary}",
                "",
                "| Operation | Target | Field | Current | Proposed |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for operation in draft.operations:
            target = operation.source_id or "source"
            if operation.step_id:
                target = f"{target}/{operation.step_id}"
            lines.append(
                "| "
                + " | ".join(
                    [
                        operation.operation_type,
                        target,
                        operation.field_path,
                        json.dumps(operation.current_value, sort_keys=True) if operation.current_value is not None else "null",
                        json.dumps(operation.proposed_value, sort_keys=True),
                    ]
                )
                + " |"
            )
        lines.append("")
    if not export.drafts:
        lines.append("- None")
    lines.extend(["", "## Blockers"])
    lines.extend([f"- {item}" for item in export.blockers] or ["- None"])
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {item}" for item in export.warnings] or ["- None"])
    lines.extend(["", "## Next Steps"])
    lines.extend([f"- {item}" for item in export.next_steps] or ["- None"])
    lines.extend(["", "## Evidence Chain"])
    lines.extend([f"- {item}" for item in export.evidence_chain])
    return "\n".join(lines) + "\n"


def render_achievement_route_source_edit_patch_draft_csv(
    export: AchievementRouteSourceEditPatchDraftExport,
) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "draft_id",
            "candidate_id",
            "item_id",
            "priority",
            "remediation_type",
            "reviewer",
            "source_id",
            "step_id",
            "manifest_path",
            "operation_id",
            "operation_type",
            "target_type",
            "field_path",
            "current_value",
            "proposed_value",
            "required_review",
            "evidence_refs",
        ]
    )
    for draft in export.drafts:
        for operation in draft.operations:
            writer.writerow(
                [
                    draft.draft_id,
                    draft.candidate_id,
                    draft.item_id,
                    draft.priority,
                    draft.remediation_type,
                    draft.reviewer,
                    draft.source_id or "",
                    draft.step_id or "",
                    draft.source_manifest_path or "",
                    operation.operation_id,
                    operation.operation_type,
                    operation.target_type,
                    operation.field_path,
                    json.dumps(operation.current_value, sort_keys=True) if operation.current_value is not None else "",
                    json.dumps(operation.proposed_value, sort_keys=True),
                    ";".join(operation.required_review),
                    ";".join(operation.evidence_refs),
                ]
            )
    return buffer.getvalue()


def apply_achievement_route_source_edit_patch_draft(
    request: AchievementRouteSourceEditPatchApplyRequest,
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteSourceEditPatchApplyRecord:
    if not request.confirmed_manual_review:
        raise ValueError("Source edit patch apply requires confirmed_manual_review=true.")
    patch_export = build_achievement_route_source_edit_patch_draft(source_root, audit_root)
    draft_by_id = {draft.draft_id: draft for draft in patch_export.drafts}
    draft = draft_by_id.get(request.draft_id)
    if draft is None:
        raise ValueError(f"Source edit patch draft {request.draft_id} is not available for apply.")

    manifests = [
        manifest
        for manifest in load_achievement_route_source_manifests(source_root)
        if isinstance(manifest, AchievementRouteSourceManifest)
    ]
    source_manifest = next((manifest for manifest in manifests if manifest.source_id == draft.source_id), None)
    output_source_id = request.output_source_id or f"{draft.source_id or 'achievement-route-source'}:patch-draft:{_slug(draft.candidate_id)}"
    manifest = _copy_manifest_for_patch_apply(source_manifest, output_source_id, request.reviewer, request.notes)
    _apply_route_source_patch_operations(manifest, draft.operations)

    source_root.mkdir(parents=True, exist_ok=True)
    output_path = _reviewed_manifest_path(source_root, output_source_id)
    output_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

    record = AchievementRouteSourceEditPatchApplyRecord(
        event_id=f"route-source-edit-patch-apply:{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
        draft_id=draft.draft_id,
        candidate_id=draft.candidate_id,
        source_id=draft.source_id,
        output_source_id=output_source_id,
        output_manifest_path=str(output_path),
        operation_count=len(draft.operations),
        applied_at=datetime.now(UTC),
        reviewer=request.reviewer,
        notes=_unique([note.strip() for note in request.notes if note.strip()]),
        evidence_refs=_unique([*draft.evidence_refs, *[ref.strip() for ref in request.evidence_refs if ref.strip()]]),
    )
    audit_root.mkdir(parents=True, exist_ok=True)
    path = audit_root / "source_edit_patch_apply_audit.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(record.model_dump_json() + "\n")
    return record


def list_achievement_route_source_edit_patch_apply_audits(
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    *,
    reviewer: str | None = None,
    draft_id: str | None = None,
    output_source_id: str | None = None,
    limit: int = 25,
) -> AchievementRouteSourceEditPatchApplyAuditList:
    path = audit_root / "source_edit_patch_apply_audit.jsonl"
    records: list[AchievementRouteSourceEditPatchApplyRecord] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = AchievementRouteSourceEditPatchApplyRecord.model_validate_json(line)
            except ValidationError:
                continue
            if reviewer and record.reviewer != reviewer:
                continue
            if draft_id and record.draft_id != draft_id:
                continue
            if output_source_id and record.output_source_id != output_source_id:
                continue
            records.append(record)
    records = sorted(records, key=lambda item: item.applied_at, reverse=True)[: max(1, min(limit, 200))]
    return AchievementRouteSourceEditPatchApplyAuditList(
        records=records,
        filters={"reviewer": reviewer, "draft_id": draft_id, "output_source_id": output_source_id, "limit": limit},
    )


def render_achievement_route_source_edit_patch_apply_audit_markdown(
    audit_list: AchievementRouteSourceEditPatchApplyAuditList,
) -> str:
    lines = [
        "# Achievement Route Source Edit Patch Apply Audit",
        "",
        f"- Records: {len(audit_list.records)}",
        f"- Boundary: {audit_list.boundary}",
        "",
        "| Applied At | Reviewer | Draft | Output Source | Operations | Manifest Path |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for record in audit_list.records:
        lines.append(
            "| "
            + " | ".join(
                [
                    record.applied_at.isoformat(),
                    record.reviewer,
                    record.draft_id,
                    record.output_source_id,
                    str(record.operation_count),
                    record.output_manifest_path,
                ]
            )
            + " |"
        )
    if not audit_list.records:
        lines.append("| none | none | none | none | none | none |")
    return "\n".join(lines) + "\n"


def render_achievement_route_source_edit_patch_apply_audit_csv(
    audit_list: AchievementRouteSourceEditPatchApplyAuditList,
) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "event_id",
            "applied_at",
            "reviewer",
            "draft_id",
            "candidate_id",
            "source_id",
            "output_source_id",
            "output_manifest_path",
            "operation_count",
            "notes",
            "evidence_refs",
        ]
    )
    for record in audit_list.records:
        writer.writerow(
            [
                record.event_id,
                record.applied_at.isoformat(),
                record.reviewer,
                record.draft_id,
                record.candidate_id,
                record.source_id or "",
                record.output_source_id,
                record.output_manifest_path,
                record.operation_count,
                ";".join(record.notes),
                ";".join(record.evidence_refs),
            ]
        )
    return buffer.getvalue()


def promote_draft_achievement_route_source_to_reviewed(
    request: AchievementRouteDraftSourcePromotionRequest,
    source_root: Path = ACHIEVEMENT_ROUTE_SOURCE_ROOT,
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
) -> AchievementRouteDraftSourcePromotionRecord:
    if not request.confirmed_reviewed:
        raise ValueError("Draft source promotion requires confirmed_reviewed=true.")
    manifests = [
        manifest
        for manifest in load_achievement_route_source_manifests(source_root)
        if isinstance(manifest, AchievementRouteSourceManifest)
    ]
    draft = next((manifest for manifest in manifests if manifest.source_id == request.draft_source_id), None)
    if draft is None:
        raise ValueError(f"Draft source manifest {request.draft_source_id} was not found.")
    if draft.source_status != "draft":
        raise ValueError(f"Source manifest {request.draft_source_id} is {draft.source_status}, not draft.")
    if not draft.steps:
        raise ValueError("Cannot promote a draft source manifest with no steps.")

    reviewed_source_id = request.reviewed_source_id or f"{request.draft_source_id}:reviewed"
    manifest_path = _reviewed_manifest_path(source_root, reviewed_source_id)
    if manifest_path.exists() and not request.overwrite_existing:
        raise FileExistsError(f"Reviewed achievement route manifest already exists: {manifest_path.as_posix()}")

    notes = request.review_notes or ["Human reviewer promoted this draft source manifest after source patch apply review."]
    reviewed_manifest = draft.model_copy(
        deep=True,
        update={
            "source_id": reviewed_source_id,
            "source_status": "reviewed",
            "reviewed_by": request.reviewer,
            "reviewed_at": datetime.now(UTC).date().isoformat(),
            "assumptions": _unique(
                [
                    *draft.assumptions,
                    "This manifest was promoted from a draft source manifest through the reviewed gate.",
                    *notes,
                ]
            ),
            "steps": [
                step.model_copy(
                    update={
                        "source_id": reviewed_source_id,
                        "source_status": "reviewed",
                        "evidence_refs": _unique([*step.evidence_refs, reviewed_source_id, *request.evidence_refs]),
                        "assumptions": _unique(
                            [
                                *step.assumptions,
                                "Human reviewer promoted this draft source patch output for route planning.",
                            ]
                        ),
                    }
                )
                for step in draft.steps
            ],
        },
    )
    source_root.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(reviewed_manifest.model_dump_json(indent=2), encoding="utf-8")

    record = AchievementRouteDraftSourcePromotionRecord(
        event_id=f"route-draft-source-promotion:{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}:{_safe_identifier(reviewed_source_id)}",
        draft_source_id=request.draft_source_id,
        reviewed_source_id=reviewed_source_id,
        reviewer=request.reviewer,
        promoted_at=datetime.now(UTC),
        manifest_path=manifest_path.as_posix(),
        step_count=len(reviewed_manifest.steps),
        review_notes=_unique([note.strip() for note in notes if note.strip()]),
        evidence_refs=_unique([*draft.source_refs, *request.evidence_refs, *[ref for step in reviewed_manifest.steps for ref in step.evidence_refs]]),
        planner_ingestion_status="ready",
    )
    audit_root.mkdir(parents=True, exist_ok=True)
    path = audit_root / "draft_source_promotion_audit.jsonl"
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(record.model_dump_json() + "\n")
    return record


def list_achievement_route_draft_source_promotion_audits(
    audit_root: Path = ACHIEVEMENT_ROUTE_AUDIT_ROOT,
    *,
    reviewer: str | None = None,
    draft_source_id: str | None = None,
    reviewed_source_id: str | None = None,
    limit: int = 25,
) -> AchievementRouteDraftSourcePromotionAuditList:
    path = audit_root / "draft_source_promotion_audit.jsonl"
    records: list[AchievementRouteDraftSourcePromotionRecord] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                record = AchievementRouteDraftSourcePromotionRecord.model_validate_json(line)
            except ValidationError:
                continue
            if reviewer and record.reviewer != reviewer:
                continue
            if draft_source_id and record.draft_source_id != draft_source_id:
                continue
            if reviewed_source_id and record.reviewed_source_id != reviewed_source_id:
                continue
            records.append(record)
    records = sorted(records, key=lambda item: item.promoted_at, reverse=True)[: max(1, min(limit, 200))]
    return AchievementRouteDraftSourcePromotionAuditList(
        records=records,
        filters={"reviewer": reviewer, "draft_source_id": draft_source_id, "reviewed_source_id": reviewed_source_id, "limit": limit},
    )


def render_achievement_route_draft_source_promotion_audit_markdown(
    audit_list: AchievementRouteDraftSourcePromotionAuditList,
) -> str:
    lines = [
        "# Achievement Route Draft Source Promotion Audit",
        "",
        f"- Records: {len(audit_list.records)}",
        f"- Boundary: {audit_list.boundary}",
        "",
        "| Promoted At | Reviewer | Draft Source | Reviewed Source | Steps | Manifest Path |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for record in audit_list.records:
        lines.append(
            "| "
            + " | ".join(
                [
                    record.promoted_at.isoformat(),
                    record.reviewer,
                    record.draft_source_id,
                    record.reviewed_source_id,
                    str(record.step_count),
                    record.manifest_path,
                ]
            )
            + " |"
        )
    if not audit_list.records:
        lines.append("| none | none | none | none | none | none |")
    return "\n".join(lines) + "\n"


def render_achievement_route_draft_source_promotion_audit_csv(
    audit_list: AchievementRouteDraftSourcePromotionAuditList,
) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "event_id",
            "promoted_at",
            "reviewer",
            "draft_source_id",
            "reviewed_source_id",
            "manifest_path",
            "step_count",
            "planner_ingestion_status",
            "review_notes",
            "evidence_refs",
        ]
    )
    for record in audit_list.records:
        writer.writerow(
            [
                record.event_id,
                record.promoted_at.isoformat(),
                record.reviewer,
                record.draft_source_id,
                record.reviewed_source_id,
                record.manifest_path,
                record.step_count,
                record.planner_ingestion_status,
                ";".join(record.review_notes),
                ";".join(record.evidence_refs),
            ]
        )
    return buffer.getvalue()


def _build_segments(
    steps: list[AchievementRouteStep],
    ready: list[str],
    blocked: list[str],
    time_gated: list[str],
) -> list[AchievementRouteSegment]:
    segment_index: dict[str, list[AchievementRouteStep]] = {}
    for step in steps:
        segment_index.setdefault(step.map_name, []).append(step)
    segments: list[AchievementRouteSegment] = []
    for map_name, map_steps in segment_index.items():
        ready_ids = [step.step_id for step in map_steps if step.step_id in ready]
        blocked_ids = [step.step_id for step in map_steps if step.step_id in blocked]
        gated_ids = [step.step_id for step in map_steps if step.step_id in time_gated]
        total = sum(step.estimated_minutes for step in map_steps if step.step_id in ready_ids)
        notes = []
        if blocked_ids:
            notes.append("Resolve prerequisites or enable group-content planning before adding blocked steps.")
        if gated_ids:
            notes.append("Treat daily/weekly labels as scheduling gates and verify current reset state.")
        segments.append(
            AchievementRouteSegment(
                segment_id=f"segment:{_slug(map_name)}",
                map_name=map_name,
                region=map_steps[0].region,
                ready_step_ids=ready_ids,
                blocked_step_ids=blocked_ids,
                time_gated_step_ids=gated_ids,
                total_ready_minutes=total,
                notes=notes,
            )
        )
    return sorted(segments, key=lambda segment: (not segment.ready_step_ids, segment.map_name))


def _fit_ready_steps(steps: list[AchievementRouteStep], ready_ids: list[str], minutes: int) -> list[str]:
    fitted: list[str] = []
    spent = 0
    for step in sorted((step for step in steps if step.step_id in ready_ids), key=lambda item: item.estimated_minutes):
        if spent + step.estimated_minutes > minutes and fitted:
            continue
        fitted.append(step.step_id)
        spent += step.estimated_minutes
        if spent >= minutes:
            break
    return fitted


def _build_actions(
    steps: list[AchievementRouteStep],
    segments: list[AchievementRouteSegment],
    ready_ids: list[str],
    blocked_ids: list[str],
    time_gated_ids: list[str],
    minutes: int,
) -> list[AchievementRouteAction]:
    step_by_id = {step.step_id: step for step in steps}
    actions: list[AchievementRouteAction] = []
    for segment in segments:
        segment_ready = [step_id for step_id in segment.ready_step_ids if step_id in ready_ids]
        if segment_ready:
            actions.append(
                AchievementRouteAction(
                    action_id=f"action:run:{segment.segment_id}",
                    action_type="run_segment",
                    title=f"Run {segment.map_name} segment",
                    step_ids=segment_ready,
                    reason=f"Fits inside the {minutes}-minute planning window with map-local objectives grouped together.",
                )
            )
    for step_id in time_gated_ids:
        if step_id in ready_ids:
            step = step_by_id[step_id]
            actions.append(
                AchievementRouteAction(
                    action_id=f"action:gate:{step_id}",
                    action_type="do_time_gated_step",
                    title=f"Schedule {step.title}",
                    step_ids=[step_id],
                    reason=f"Marked as {step.time_gate}; verify reset state before relying on it.",
                )
            )
    for step_id in blocked_ids:
        step = step_by_id[step_id]
        missing = ", ".join(step.prerequisite_ids) or "group-content opt-in"
        actions.append(
            AchievementRouteAction(
                action_id=f"action:blocker:{step_id}",
                action_type="unlock_prerequisite" if step.prerequisite_ids else "postpone_blocked_step",
                title=f"Resolve blocker for {step.title}",
                step_ids=[step_id],
                reason=f"Missing prerequisite or planning permission: {missing}.",
            )
        )
    return actions


def _step_titles(step_by_id: dict[str, AchievementRouteStep], step_ids: list[str]) -> str:
    return ", ".join(step_by_id[step_id].title for step_id in step_ids if step_id in step_by_id)


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _set_delta(candidate_values: list[str], baseline_values: list[str]) -> tuple[list[str], list[str]]:
    candidate = set(candidate_values)
    baseline = set(baseline_values)
    return sorted(candidate - baseline), sorted(baseline - candidate)


def _review_route_step_quality(
    step: AchievementRouteStep,
    manifest: AchievementRouteSourceManifest,
    missing_achievement_ids: list[int],
) -> AchievementRouteStepQuality:
    score = 100.0
    flags: list[str] = []
    remediation: list[str] = []
    evidence_complete = bool(step.evidence_refs or manifest.source_refs)
    if not evidence_complete:
        score -= 25
        flags.append("evidence_gap")
        remediation.append(f"Add official source refs or reviewed evidence refs for {step.step_id}.")

    map_risk: Literal["low", "medium", "high"] = "low"
    assumption_text = " ".join([*manifest.assumptions, *step.assumptions]).lower()
    if step.map_name == "Unmapped Achievement Review" or "unambiguous map" in assumption_text:
        map_risk = "high"
        score -= 20
        flags.append("map_inference_high")
        remediation.append(f"Review map inference for {step.step_id} before release.")
    elif "inferred from official achievement text" in assumption_text:
        map_risk = "medium"
        score -= 10
        flags.append("map_inference_medium")

    gate_risk: Literal["low", "medium", "high"] = "low"
    if step.time_gate in {"daily", "weekly"}:
        gate_risk = "medium"
        score -= 8
        flags.append(f"{step.time_gate}_time_gate")
        remediation.append(f"Confirm current {step.time_gate} reset or rotation context for {step.step_id}.")

    missing_official_id = bool(step.official_achievement_id and step.official_achievement_id in missing_achievement_ids)
    if missing_official_id:
        score -= 30
        flags.append("missing_official_achievement_id")
        remediation.append(f"Resolve missing official achievement id {step.official_achievement_id} before release.")
    if step.official_achievement_id is None:
        score -= 5
        flags.append("no_official_achievement_id")

    return AchievementRouteStepQuality(
        step_id=step.step_id,
        source_id=manifest.source_id,
        title=step.title,
        official_achievement_id=step.official_achievement_id,
        quality_score=max(0.0, round(score, 1)),
        evidence_complete=evidence_complete,
        map_inference_risk=map_risk,
        time_gate_risk=gate_risk,
        missing_official_id=missing_official_id,
        review_flags=_unique(flags),
        remediation=_unique(remediation),
    )


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 1)


def _route_remediation_item(
    *,
    remediation_type: Literal["evidence_backfill", "map_review", "time_gate_review", "official_id_backfill"],
    priority: Literal["P0", "P1", "P2"],
    step: AchievementRouteStepQuality,
    problem: str,
    action: str,
    prompt: str,
) -> AchievementRouteRemediationItem:
    return AchievementRouteRemediationItem(
        item_id=f"{priority.lower()}:{remediation_type}:{_slug(step.source_id)}:{_slug(step.step_id)}",
        priority=priority,
        remediation_type=remediation_type,
        source_id=step.source_id,
        step_id=step.step_id,
        title=step.title,
        problem=problem,
        recommended_action=action,
        reviewer_prompt=prompt,
        evidence_refs=[
            f"source:{step.source_id}",
            f"step:{step.step_id}",
            "/api/v1/achievement-routes/source-quality",
        ],
    )


def _route_remediation_next_actions(items: list[AchievementRouteRemediationItem]) -> list[str]:
    if not items:
        return ["No route source remediation is open; continue release readiness review."]
    actions: list[str] = []
    if any(item.priority == "P0" for item in items):
        actions.append("Resolve P0 missing official id or missing source-manifest items before release.")
    if any(item.remediation_type == "evidence_backfill" for item in items):
        actions.append("Backfill official evidence refs for P1 evidence gaps and re-run source quality review.")
    if any(item.remediation_type == "map_review" for item in items):
        actions.append("Confirm inferred or unmapped route locations with official/in-game evidence.")
    if any(item.remediation_type == "time_gate_review" for item in items):
        actions.append("Review daily/weekly gate wording so player plans remain schedule-aware.")
    actions.append("After edits, promote through the existing reviewed source gate and verify release readiness.")
    return _unique(actions)


def _route_backfill_candidate(item: AchievementRouteRemediationItem) -> AchievementRouteBackfillCandidate:
    suggested_fields: dict[str, Any] = {}
    required_review = ["human_reviewer_confirmation", "source_manifest_manual_edit"]
    if item.remediation_type == "official_id_backfill":
        suggested_fields = {
            "official_achievement_id": "replace_or_remove_missing_id",
            "evidence_refs": ["official:/v2/achievements"],
        }
        required_review.append("official_api_refetch")
    elif item.remediation_type == "evidence_backfill":
        suggested_fields = {"evidence_refs": ["official_wiki_or_api_ref_required"]}
        required_review.append("evidence_source_check")
    elif item.remediation_type == "map_review":
        suggested_fields = {"map_name": "review_required", "region": "review_required"}
        required_review.append("in_game_or_official_location_check")
    elif item.remediation_type == "time_gate_review":
        suggested_fields = {"time_gate": "confirm_daily_weekly_or_none", "assumptions": ["reset_or_rotation_review_required"]}
        required_review.append("current_reset_context_check")
    elif item.remediation_type == "source_manifest_backfill":
        suggested_fields = {"source_status": "reviewed", "source_refs": ["official_source_required"], "steps": "reviewed_steps_required"}
        required_review.append("reviewed_source_manifest_creation")
    return AchievementRouteBackfillCandidate(
        candidate_id=f"backfill:{_slug(item.item_id)}",
        item_id=item.item_id,
        priority=item.priority,
        remediation_type=item.remediation_type,
        source_id=item.source_id,
        step_id=item.step_id,
        title=item.title,
        suggested_fields=suggested_fields,
        rationale=item.recommended_action,
        required_review=_unique(required_review),
        evidence_refs=item.evidence_refs,
    )


def _route_source_edit_patch_operations(
    candidate: AchievementRouteBackfillCandidate,
    manifest: AchievementRouteSourceManifest | None,
) -> list[AchievementRouteSourceEditPatchOperation]:
    if manifest is None and candidate.step_id is None:
        return []
    operations: list[AchievementRouteSourceEditPatchOperation] = []
    step = None
    if manifest and candidate.step_id:
        step = next((item for item in manifest.steps if item.step_id == candidate.step_id), None)
    for field_name, proposed_value in candidate.suggested_fields.items():
        target_type: Literal["source_manifest", "route_step"] = "route_step"
        current_value: Any | None = None
        operation_type: Literal["add", "replace", "review"] = "review"
        if field_name in {"source_status", "source_refs", "steps"}:
            target_type = "source_manifest"
            current_value = getattr(manifest, field_name, None) if manifest else None
        elif step is not None:
            current_value = getattr(step, field_name, None)

        if current_value in (None, "", [], {}):
            operation_type = "add"
        elif current_value != proposed_value:
            operation_type = "replace"

        operations.append(
            AchievementRouteSourceEditPatchOperation(
                operation_id=f"patch-op:{_slug(candidate.candidate_id)}:{_slug(field_name)}",
                candidate_id=candidate.candidate_id,
                operation_type=operation_type,
                target_type=target_type,
                source_id=candidate.source_id,
                step_id=candidate.step_id if target_type == "route_step" else None,
                field_path=f"steps[{candidate.step_id}].{field_name}" if target_type == "route_step" else field_name,
                current_value=current_value,
                proposed_value=proposed_value,
                rationale=candidate.rationale,
                evidence_refs=candidate.evidence_refs,
                required_review=candidate.required_review,
            )
        )
    return operations


def _copy_manifest_for_patch_apply(
    manifest: AchievementRouteSourceManifest | None,
    output_source_id: str,
    reviewer: str,
    notes: list[str],
) -> AchievementRouteSourceManifest:
    if manifest is None:
        return AchievementRouteSourceManifest(
            source_id=output_source_id,
            title="Draft source edit patch manifest",
            source_status="draft",
            reviewed_by=reviewer,
            reviewed_at=datetime.now(UTC).isoformat(),
            assumptions=_unique(["Draft manifest created from source edit patch operations.", *notes]),
            steps=[],
        )
    return manifest.model_copy(
        deep=True,
        update={
            "source_id": output_source_id,
            "source_status": "draft",
            "reviewed_by": reviewer,
            "reviewed_at": datetime.now(UTC).isoformat(),
            "assumptions": _unique([*manifest.assumptions, "Draft manifest created from source edit patch operations.", *notes]),
        },
    )


def _apply_route_source_patch_operations(
    manifest: AchievementRouteSourceManifest,
    operations: list[AchievementRouteSourceEditPatchOperation],
) -> None:
    step_by_id = {step.step_id: step for step in manifest.steps}
    for operation in operations:
        if operation.target_type == "source_manifest":
            _set_manifest_field(manifest, operation.field_path, operation.proposed_value)
            continue
        if not operation.step_id:
            continue
        step = step_by_id.get(operation.step_id)
        if step is None:
            step = AchievementRouteStep(
                step_id=operation.step_id,
                title=f"Draft step {operation.step_id}",
                step_type="achievement",
                map_name="Unmapped Achievement Review",
                region="Review Required",
                objective="Review and complete draft source edit patch step fields before promotion.",
                advances_goal_id="custom_achievement_route",
                estimated_minutes=10,
                assumptions=["Draft step created from source edit patch operation; review required before promotion."],
                source_id=manifest.source_id,
                source_status="draft",
            )
            manifest.steps.append(step)
            step_by_id[step.step_id] = step
        field_name = operation.field_path.split(".")[-1]
        _set_step_field(step, field_name, operation.proposed_value)


def _set_manifest_field(manifest: AchievementRouteSourceManifest, field_name: str, value: Any) -> None:
    if field_name == "source_refs" and isinstance(value, list):
        manifest.source_refs = _unique([str(item) for item in value])
    elif field_name == "source_status" and value in {"draft", "reviewed", "disabled"}:
        manifest.source_status = value
    elif field_name == "assumptions" and isinstance(value, list):
        manifest.assumptions = _unique([str(item) for item in value])


def _set_step_field(step: AchievementRouteStep, field_name: str, value: Any) -> None:
    if field_name == "official_achievement_id":
        if isinstance(value, int):
            step.official_achievement_id = value
    elif field_name == "evidence_refs" and isinstance(value, list):
        step.evidence_refs = _unique([str(item) for item in value])
    elif field_name == "map_name" and isinstance(value, str):
        step.map_name = value
    elif field_name == "region" and isinstance(value, str):
        step.region = value
    elif field_name == "time_gate" and value in {"none", "daily", "weekly"}:
        step.time_gate = value
    elif field_name == "assumptions" and isinstance(value, list):
        step.assumptions = _unique([str(item) for item in value])


def _slug(value: str) -> str:
    return value.lower().replace(" ", "-").replace(":", "")


def _reviewed_source_id(source_id: str) -> str:
    if source_id.startswith("kb:achievement-routes:"):
        return source_id
    return f"kb:achievement-routes:{_slug(source_id)}:reviewed"


def _reviewed_manifest_path(source_root: Path, source_id: str) -> Path:
    safe_name = _safe_identifier(source_id)
    return source_root / f"{safe_name}.json"


def _safe_identifier(value: str) -> str:
    safe_name = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in value.lower())
    return safe_name.strip("_") or "achievement_route"


def _official_progress_status(
    progress: OfficialAccountAchievementProgress | None,
) -> tuple[RouteAccountProgressStatus, str | None]:
    if progress is None:
        return "unknown", "No account achievement progress payload supplied."
    if progress.done is True:
        return "complete", "Official account achievement payload marks this achievement complete."
    if progress.max and progress.current is not None:
        if progress.current >= progress.max:
            return "complete", f"Official account progress is {progress.current}/{progress.max}."
        if progress.current > 0:
            return "in_progress", f"Official account progress is {progress.current}/{progress.max}."
        return "not_started", f"Official account progress is {progress.current}/{progress.max}."
    if progress.current:
        return "in_progress", f"Official account progress current value is {progress.current}."
    return "not_started", "Official account progress has no completed value."


def _infer_official_route_location(detail: OfficialAchievementDetail) -> tuple[str, str, str]:
    text = f"{detail.name} {detail.description or ''} {detail.requirement or ''} {detail.locked_text or ''}".lower()
    known_locations = [
        ("bloodstone fen", "Bloodstone Fen", "Maguuma Wastes"),
        ("ember bay", "Ember Bay", "Ring of Fire"),
        ("bitterfrost", "Bitterfrost Frontier", "Shiverpeak Mountains"),
        ("dragonfall", "Dragonfall", "Crystal Desert"),
        ("fractals", "Fractals of the Mists", "Mistlock Observatory"),
        ("fractal", "Fractals of the Mists", "Mistlock Observatory"),
    ]
    for marker, map_name, region in known_locations:
        if marker in text:
            return (
                map_name,
                region,
                f"Map inferred from official achievement text keyword: {map_name}.",
            )
    return (
        "Unmapped Achievement Review",
        "Unknown",
        "Official achievement payload did not include an unambiguous map; review required.",
    )


def _infer_official_time_gate(detail: OfficialAchievementDetail) -> RouteTimeGate:
    text = f"{detail.name} {detail.description or ''} {detail.requirement or ''}".lower()
    flags = {flag.lower() for flag in detail.flags}
    if "weekly" in text or "weekly" in flags:
        return "weekly"
    if "daily" in text or "daily" in flags:
        return "daily"
    return "none"


def _infer_official_group_required(detail: OfficialAchievementDetail) -> bool:
    text = f"{detail.name} {detail.description or ''} {detail.requirement or ''}".lower()
    return any(marker in text for marker in ("fractal", "raid", "strike", "meta-event", "meta event", "squad"))


def _estimate_official_minutes(detail: OfficialAchievementDetail, group_required: bool) -> int:
    if group_required:
        return 25
    if detail.bits:
        return min(max(len(detail.bits) * 5, 10), 45)
    return 15


def _official_objective(detail: OfficialAchievementDetail) -> str:
    for value in (detail.requirement, detail.description, detail.locked_text):
        if value and value.strip():
            return " ".join(value.strip().split())
    return "Review the official achievement detail and convert it into a player-verified route step."


def _official_details_from_payload(payload: Any) -> list[OfficialAchievementDetail]:
    rows = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) else []
    details: list[OfficialAchievementDetail] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            details.append(OfficialAchievementDetail.model_validate(row))
        except ValidationError:
            continue
    return details


def _gateway_status_value(result) -> str:
    status = getattr(result, "status", "unknown")
    return getattr(status, "value", str(status))
