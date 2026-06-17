from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.acquisition.maturity import build_acquisition_maturity_report
from gw2radar.acquisition.promotion_queue import AcquisitionPromotionQueue, build_acquisition_promotion_queue


class AcquisitionPromotionReadinessReport(BaseModel):
    schema_version: str = "gw2radar.acquisition_promotion_readiness.v1"
    ready: bool
    maturity_label: str
    overall_score: float
    queue_item_count: int
    blocker_count: int
    warning_count: int
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    queue_counts_by_type: dict[str, int] = Field(default_factory=dict)
    next_operator_steps: list[str] = Field(default_factory=list)


def build_acquisition_promotion_readiness_report(session: Session) -> AcquisitionPromotionReadinessReport:
    maturity = build_acquisition_maturity_report(session)
    queue = build_acquisition_promotion_queue(session)
    blockers = _blockers(queue)
    warnings = _warnings(queue)
    if maturity.maturity_label == "early":
        blockers.append("Acquisition maturity label is `early`.")
    elif maturity.maturity_label == "partial":
        warnings.append("Acquisition maturity is still developing; promote only low-risk reviewed content.")

    return AcquisitionPromotionReadinessReport(
        ready=not blockers,
        maturity_label=maturity.maturity_label,
        overall_score=maturity.overall_score,
        queue_item_count=queue.item_count,
        blocker_count=len(blockers),
        warning_count=len(warnings),
        blockers=blockers,
        warnings=warnings,
        queue_counts_by_type=queue.counts_by_type,
        next_operator_steps=_next_steps(blockers, warnings, queue),
    )


def render_acquisition_promotion_readiness_markdown(report: AcquisitionPromotionReadinessReport) -> str:
    lines = [
        "# Acquisition Promotion Readiness Gate",
        "",
        f"- schema_version: `{report.schema_version}`",
        f"- ready: `{str(report.ready).lower()}`",
        f"- maturity_label: `{report.maturity_label}`",
        f"- overall_score: `{report.overall_score:.2f}`",
        f"- queue_item_count: `{report.queue_item_count}`",
        f"- blocker_count: `{report.blocker_count}`",
        f"- warning_count: `{report.warning_count}`",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {blocker}" for blocker in report.blockers) if report.blockers else lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {warning}" for warning in report.warnings) if report.warnings else lines.append("- none")
    lines.extend(["", "## Queue Counts", ""])
    if report.queue_counts_by_type:
        lines.extend(f"- {key}: `{value}`" for key, value in sorted(report.queue_counts_by_type.items()))
    else:
        lines.append("- none")
    lines.extend(["", "## Next Operator Steps", ""])
    if report.next_operator_steps:
        lines.extend(f"- {step}" for step in report.next_operator_steps)
    else:
        lines.append("- Continue normal reviewed source import and KB rule promotion cadence.")
    return "\n".join(lines) + "\n"


def _blockers(queue: AcquisitionPromotionQueue) -> list[str]:
    blockers: list[str] = []
    counts = queue.counts_by_type
    if counts.get("orphan_raw_evidence"):
        blockers.append("Resolve orphan raw evidence before promotion.")
    if counts.get("rule_needs_raw_evidence"):
        blockers.append("Attach raw evidence ids to KnowledgeRule records before enabling them.")
    if counts.get("source_needs_raw_evidence"):
        blockers.append("Import raw evidence for registered acquisition sources before promotion.")
    return blockers


def _warnings(queue: AcquisitionPromotionQueue) -> list[str]:
    warnings: list[str] = []
    counts = queue.counts_by_type
    if counts.get("source_needs_kb_article"):
        warnings.append("Some evidence-backed sources still need reviewed KB articles.")
    if counts.get("raw_evidence_needs_rule_candidate"):
        warnings.append("Some raw evidence is not yet distilled into disabled KnowledgeRule candidates.")
    return warnings


def _next_steps(blockers: list[str], warnings: list[str], queue: AcquisitionPromotionQueue) -> list[str]:
    if blockers:
        return queue.next_operator_steps[:5]
    if warnings:
        return [
            "Promote only reviewed, source-attributed summaries while warning items remain.",
            *queue.next_operator_steps[:4],
        ]
    return ["Promotion gate is clear for reviewed KB articles and disabled rule candidates."]
