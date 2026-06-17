from collections import Counter

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.acquisition.readiness import build_acquisition_readiness_report
from gw2radar.acquisition.repository import get_policy, list_jobs, list_sources
from gw2radar.acquisition.seed_packs import get_acquisition_seed_pack


class AcquisitionMaturityDimension(BaseModel):
    dimension_id: str
    label: str
    score: float = Field(ge=0.0, le=1.0)
    summary: str
    gaps: list[str] = Field(default_factory=list)


class AcquisitionMaturityReport(BaseModel):
    schema_version: str = "gw2radar.acquisition_maturity.v1"
    overall_score: float = Field(ge=0.0, le=1.0)
    maturity_label: str
    source_count: int
    job_count: int
    dimensions: list[AcquisitionMaturityDimension]
    next_priorities: list[str]


def build_acquisition_maturity_report(session: Session) -> AcquisitionMaturityReport:
    sources = list_sources(session)
    jobs = list_jobs(session)
    readiness = build_acquisition_readiness_report(session)
    seed_pack = get_acquisition_seed_pack("mvp_baseline")
    policy_count = sum(1 for source in sources if get_policy(session, source.source_id) is not None)
    job_counts = Counter(job.status.value if hasattr(job.status, "value") else str(job.status) for job in jobs)

    dimensions = [
        _seed_dimension(len(sources), len(seed_pack.entries)),
        _policy_dimension(policy_count, len(sources)),
        _job_dimension(job_counts, len(jobs)),
        _readiness_dimension(readiness.ready, len(readiness.blockers)),
        _report_eligibility_dimension(readiness.paid_report_source_count, readiness.strong_recommendation_source_count),
    ]
    overall = round(sum(dimension.score for dimension in dimensions) / len(dimensions), 3)
    next_priorities = _next_priorities(dimensions)
    return AcquisitionMaturityReport(
        overall_score=overall,
        maturity_label=_label_for_score(overall),
        source_count=len(sources),
        job_count=len(jobs),
        dimensions=dimensions,
        next_priorities=next_priorities,
    )


def render_acquisition_maturity_markdown(report: AcquisitionMaturityReport) -> str:
    lines = [
        "# Acquisition Maturity And Coverage",
        "",
        f"- schema_version: `{report.schema_version}`",
        f"- overall_score: `{report.overall_score:.3f}`",
        f"- maturity_label: `{report.maturity_label}`",
        f"- source_count: `{report.source_count}`",
        f"- job_count: `{report.job_count}`",
        "",
        "## Dimensions",
        "",
        "| Dimension | Score | Summary | Gaps |",
        "|---|---:|---|---|",
    ]
    for dimension in report.dimensions:
        gaps = "; ".join(dimension.gaps) if dimension.gaps else "none"
        lines.append(f"| {dimension.label} | {dimension.score:.2f} | {dimension.summary} | {gaps} |")
    lines.extend(["", "## Next Priorities", ""])
    if report.next_priorities:
        lines.extend(f"- {priority}" for priority in report.next_priorities)
    else:
        lines.append("- Maintain acquisition source review, job drains, and release readiness export cadence.")
    return "\n".join(lines) + "\n"


def _seed_dimension(source_count: int, expected_count: int) -> AcquisitionMaturityDimension:
    score = min(source_count / expected_count, 1.0) if expected_count else 1.0
    gaps = [] if score >= 1.0 else ["Import the MVP acquisition seed pack."]
    return AcquisitionMaturityDimension(
        dimension_id="seed_coverage",
        label="Seed coverage",
        score=round(score, 3),
        summary=f"{source_count} registered sources versus {expected_count} MVP baseline seed entries.",
        gaps=gaps,
    )


def _policy_dimension(policy_count: int, source_count: int) -> AcquisitionMaturityDimension:
    score = policy_count / source_count if source_count else 0.0
    gaps = [] if score >= 1.0 else ["Add SourcePolicy records for every acquisition source."]
    return AcquisitionMaturityDimension(
        dimension_id="policy_coverage",
        label="Policy coverage",
        score=round(score, 3),
        summary=f"{policy_count} of {source_count} sources have explicit policies.",
        gaps=gaps,
    )


def _job_dimension(job_counts: Counter, job_count: int) -> AcquisitionMaturityDimension:
    if job_count == 0:
        score = 0.25
        gaps = ["Run at least one safe acquisition job or local import to prove the pipeline."]
    else:
        succeeded = job_counts.get("succeeded", 0)
        failed = job_counts.get("failed", 0)
        delayed = job_counts.get("delayed", 0)
        score = max(0.0, min((succeeded / job_count) - (0.2 * failed) - (0.1 * delayed), 1.0))
        gaps = []
        if failed:
            gaps.append("Review failed acquisition jobs.")
        if delayed:
            gaps.append("Drain delayed jobs after retry windows.")
        if succeeded == 0:
            gaps.append("Complete at least one acquisition job successfully.")
    return AcquisitionMaturityDimension(
        dimension_id="job_health",
        label="Job health",
        score=round(score, 3),
        summary=f"{job_count} jobs across statuses: {dict(sorted(job_counts.items())) or {'none': 0}}.",
        gaps=gaps,
    )


def _readiness_dimension(ready: bool, blocker_count: int) -> AcquisitionMaturityDimension:
    score = 1.0 if ready and blocker_count == 0 else 0.4 if ready else 0.15
    gaps = [] if score == 1.0 else ["Resolve acquisition readiness blockers and warnings before release."]
    return AcquisitionMaturityDimension(
        dimension_id="readiness_gate",
        label="Readiness gate",
        score=score,
        summary=f"Readiness ready={str(ready).lower()} with {blocker_count} blockers.",
        gaps=gaps,
    )


def _report_eligibility_dimension(paid_count: int, strong_count: int) -> AcquisitionMaturityDimension:
    if paid_count and strong_count:
        score = 1.0
    elif paid_count:
        score = 0.75
    else:
        score = 0.2
    gaps = []
    if paid_count == 0:
        gaps.append("Promote at least one reviewed source for paid report evidence.")
    if strong_count == 0:
        gaps.append("Promote at least one fresh reviewed source for strong recommendations.")
    return AcquisitionMaturityDimension(
        dimension_id="report_eligibility",
        label="Report eligibility",
        score=score,
        summary=f"{paid_count} paid-report eligible sources and {strong_count} strong-recommendation sources.",
        gaps=gaps,
    )


def _next_priorities(dimensions: list[AcquisitionMaturityDimension]) -> list[str]:
    priorities: list[str] = []
    for dimension in sorted(dimensions, key=lambda item: item.score):
        priorities.extend(dimension.gaps)
    deduped: list[str] = []
    for priority in priorities:
        if priority not in deduped:
            deduped.append(priority)
    return deduped[:5]


def _label_for_score(score: float) -> str:
    if score >= 0.85:
        return "operational"
    if score >= 0.65:
        return "maturing"
    if score >= 0.4:
        return "partial"
    return "early"
