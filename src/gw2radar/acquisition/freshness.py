from datetime import datetime, timedelta, timezone

from gw2radar.acquisition.models import (
    ActionEligibility,
    AcquisitionJob,
    AcquisitionJobStatus,
    AcquisitionSource,
    AcquisitionSourceType,
    FreshnessStatus,
    ReviewStatus,
    SourceHealth,
    SourcePolicy,
)


def evaluate_freshness(source: AcquisitionSource, latest_success_at: datetime | None = None) -> FreshnessStatus:
    if source.review_status == ReviewStatus.DEPRECATED or not source.enabled:
        return FreshnessStatus.DEPRECATED
    if latest_success_at is None:
        if source.source_type in {AcquisitionSourceType.EXPERT_RULE, AcquisitionSourceType.MANUAL_NOTE}:
            return FreshnessStatus.UNKNOWN
        return FreshnessStatus.UNKNOWN

    age = _now() - _as_aware(latest_success_at)
    fresh_after, expired_after = _thresholds_for_source(source)
    if age <= fresh_after:
        return FreshnessStatus.FRESH
    if age <= expired_after:
        return FreshnessStatus.STALE
    return FreshnessStatus.EXPIRED


def evaluate_action_eligibility(
    source: AcquisitionSource,
    policy: SourcePolicy | None,
    freshness_status: FreshnessStatus,
) -> ActionEligibility:
    reason_codes: list[str] = []
    if not source.enabled:
        reason_codes.append("source_disabled")
    if source.review_status != ReviewStatus.REVIEWED and source.review_required:
        reason_codes.append("source_not_reviewed")
    if policy is None:
        reason_codes.append("policy_missing")
    if freshness_status in {FreshnessStatus.EXPIRED, FreshnessStatus.UNKNOWN, FreshnessStatus.DEPRECATED}:
        reason_codes.append(f"freshness_{freshness_status.value}")

    policy_can_recommend = bool(policy and policy.can_drive_strong_recommendation)
    policy_can_report = bool(policy and policy.can_drive_paid_report)
    freshness_ok = freshness_status in {FreshnessStatus.FRESH, FreshnessStatus.STALE}
    reviewed_ok = source.review_status == ReviewStatus.REVIEWED or not source.review_required
    enabled_ok = source.enabled and freshness_status != FreshnessStatus.DEPRECATED

    return ActionEligibility(
        can_drive_strong_recommendation=policy_can_recommend and freshness_ok and reviewed_ok and enabled_ok,
        can_drive_paid_report=policy_can_report and enabled_ok and freshness_status != FreshnessStatus.UNKNOWN,
        reason_codes=reason_codes,
    )


def build_source_health(
    source: AcquisitionSource,
    policy: SourcePolicy | None,
    latest_job: AcquisitionJob | None,
) -> SourceHealth:
    latest_success_at = latest_job.completed_at if latest_job and latest_job.status == AcquisitionJobStatus.SUCCEEDED else None
    freshness_status = evaluate_freshness(source, latest_success_at)
    eligibility = evaluate_action_eligibility(source, policy, freshness_status)
    confidence = source.trust_level
    if freshness_status == FreshnessStatus.STALE:
        confidence = min(confidence, 0.65)
    if freshness_status in {FreshnessStatus.EXPIRED, FreshnessStatus.UNKNOWN, FreshnessStatus.DEPRECATED}:
        confidence = min(confidence, 0.4)
    if source.review_status != ReviewStatus.REVIEWED and source.review_required:
        confidence = min(confidence, 0.5)

    return SourceHealth(
        source_id=source.source_id,
        freshness_status=freshness_status,
        latest_job_status=latest_job.status if latest_job else None,
        last_checked_at=latest_job.updated_at if latest_job else None,
        last_success_at=latest_success_at,
        last_error_code=latest_job.last_error_code if latest_job else None,
        confidence=confidence,
        action_eligibility=eligibility,
        review_status=source.review_status,
        enabled=source.enabled,
    )


def _thresholds_for_source(source: AcquisitionSource) -> tuple[timedelta, timedelta]:
    if source.source_type == AcquisitionSourceType.OFFICIAL_API_PRIVATE:
        return timedelta(minutes=30), timedelta(hours=24)
    if source.source_type == AcquisitionSourceType.OFFICIAL_API_PUBLIC:
        return timedelta(hours=72), timedelta(days=30)
    if source.source_type == AcquisitionSourceType.PUBLIC_BUILD_SITE:
        return timedelta(days=7), timedelta(days=180)
    if source.source_type in {AcquisitionSourceType.GW2_WIKI, AcquisitionSourceType.DOWNLOADED_PDF}:
        return timedelta(days=30), timedelta(days=180)
    if source.source_type == AcquisitionSourceType.OFFICIAL_PATCH_NOTE:
        return timedelta(days=365), timedelta(days=3650)
    return timedelta(days=30), timedelta(days=365)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
