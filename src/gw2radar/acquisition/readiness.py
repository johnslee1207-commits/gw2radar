from collections import Counter

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.acquisition.models import AcquisitionJobStatus, FreshnessStatus, SourceHealth
from gw2radar.acquisition.repository import get_source_health, list_jobs, list_sources


class AcquisitionReadinessBlocker(BaseModel):
    source_id: str | None = None
    severity: str
    reason: str
    detail: str


class AcquisitionReadinessReport(BaseModel):
    ready: bool
    source_count: int
    reviewed_source_count: int
    enabled_source_count: int
    freshness_counts: dict[str, int] = Field(default_factory=dict)
    job_status_counts: dict[str, int] = Field(default_factory=dict)
    strong_recommendation_source_count: int
    paid_report_source_count: int
    blockers: list[AcquisitionReadinessBlocker] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


def build_acquisition_readiness_report(session: Session) -> AcquisitionReadinessReport:
    sources = list_sources(session)
    jobs = list_jobs(session)
    healths = [get_source_health(session, source.source_id) for source in sources]
    blockers = _build_blockers(healths)
    job_counts = Counter(job.status.value if hasattr(job.status, "value") else str(job.status) for job in jobs)
    failed_jobs = job_counts.get(AcquisitionJobStatus.FAILED.value, 0)
    delayed_jobs = job_counts.get(AcquisitionJobStatus.DELAYED.value, 0)
    if failed_jobs:
        blockers.append(
            AcquisitionReadinessBlocker(
                severity="error",
                reason="failed_jobs_present",
                detail=f"{failed_jobs} acquisition jobs failed and need operator review.",
            )
        )
    if delayed_jobs:
        blockers.append(
            AcquisitionReadinessBlocker(
                severity="warning",
                reason="delayed_jobs_present",
                detail=f"{delayed_jobs} acquisition jobs are delayed by rate limits or queue pressure.",
            )
        )

    freshness_counts = Counter(health.freshness_status.value for health in healths)
    recommendations = _recommendations(blockers, healths)
    hard_blockers = [blocker for blocker in blockers if blocker.severity == "error"]
    return AcquisitionReadinessReport(
        ready=not hard_blockers,
        source_count=len(sources),
        reviewed_source_count=sum(1 for source in sources if source.review_status == "reviewed"),
        enabled_source_count=sum(1 for source in sources if source.enabled),
        freshness_counts=dict(sorted(freshness_counts.items())),
        job_status_counts=dict(sorted(job_counts.items())),
        strong_recommendation_source_count=sum(
            1 for health in healths if health.action_eligibility.can_drive_strong_recommendation
        ),
        paid_report_source_count=sum(1 for health in healths if health.action_eligibility.can_drive_paid_report),
        blockers=blockers,
        recommendations=recommendations,
    )


def render_acquisition_readiness_markdown(report: AcquisitionReadinessReport) -> str:
    lines = [
        "# Acquisition Readiness",
        "",
        f"Ready: {'yes' if report.ready else 'no'}",
        f"Sources: {report.source_count}",
        f"Reviewed sources: {report.reviewed_source_count}",
        f"Enabled sources: {report.enabled_source_count}",
        f"Strong recommendation sources: {report.strong_recommendation_source_count}",
        f"Paid report sources: {report.paid_report_source_count}",
        "",
        "## Freshness",
    ]
    if report.freshness_counts:
        for status, count in report.freshness_counts.items():
            lines.append(f"- {status}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Jobs"])
    if report.job_status_counts:
        for status, count in report.job_status_counts.items():
            lines.append(f"- {status}: {count}")
    else:
        lines.append("- none")
    lines.extend(["", "## Blockers"])
    if report.blockers:
        for blocker in report.blockers:
            source = f" [{blocker.source_id}]" if blocker.source_id else ""
            lines.append(f"- {blocker.severity}: {blocker.reason}{source} - {blocker.detail}")
    else:
        lines.append("- none")
    lines.extend(["", "## Recommendations"])
    if report.recommendations:
        lines.extend(f"- {item}" for item in report.recommendations)
    else:
        lines.append("- Maintain current acquisition review cadence.")
    return "\n".join(lines) + "\n"


def _build_blockers(healths: list[SourceHealth]) -> list[AcquisitionReadinessBlocker]:
    blockers: list[AcquisitionReadinessBlocker] = []
    for health in healths:
        if health.freshness_status in {FreshnessStatus.EXPIRED, FreshnessStatus.DEPRECATED}:
            blockers.append(
                AcquisitionReadinessBlocker(
                    source_id=health.source_id,
                    severity="error",
                    reason=f"freshness_{health.freshness_status.value}",
                    detail="Source cannot support release readiness until refreshed or replaced.",
                )
            )
        elif health.freshness_status == FreshnessStatus.UNKNOWN:
            blockers.append(
                AcquisitionReadinessBlocker(
                    source_id=health.source_id,
                    severity="warning",
                    reason="freshness_unknown",
                    detail="Source has no successful acquisition job yet.",
                )
            )
        for reason in health.action_eligibility.reason_codes:
            if reason == "policy_missing":
                blockers.append(
                    AcquisitionReadinessBlocker(
                        source_id=health.source_id,
                        severity="error",
                        reason=reason,
                        detail="Source must have an explicit policy before release.",
                    )
                )
            elif reason == "source_not_reviewed":
                blockers.append(
                    AcquisitionReadinessBlocker(
                        source_id=health.source_id,
                        severity="warning",
                        reason=reason,
                        detail="Review source before using it in paid reports or high-impact guidance.",
                    )
                )
    return blockers


def _recommendations(blockers: list[AcquisitionReadinessBlocker], healths: list[SourceHealth]) -> list[str]:
    reasons = {blocker.reason for blocker in blockers}
    recommendations: list[str] = []
    if "policy_missing" in reasons:
        recommendations.append("Add SourcePolicy records for every registered acquisition source.")
    if "source_not_reviewed" in reasons:
        recommendations.append("Review or deprecate draft acquisition sources before report release.")
    if any(reason.startswith("freshness_") for reason in reasons):
        recommendations.append("Run source-specific refresh jobs or keep affected sources out of release gates.")
    if not any(health.action_eligibility.can_drive_paid_report for health in healths):
        recommendations.append("Promote at least one reviewed, attributed source for paid report evidence.")
    return recommendations
