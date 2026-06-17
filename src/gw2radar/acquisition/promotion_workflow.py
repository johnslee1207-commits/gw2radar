from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.acquisition.coverage import build_evidence_coverage_map
from gw2radar.acquisition.maturity import build_acquisition_maturity_report
from gw2radar.acquisition.promotion_queue import AcquisitionPromotionQueueItem, build_acquisition_promotion_queue
from gw2radar.acquisition.promotion_readiness import build_acquisition_promotion_readiness_report
from gw2radar.acquisition.readiness import build_acquisition_readiness_report


class AcquisitionPromotionWorkflowFilter(BaseModel):
    priority: str | None = None
    item_type: str | None = None
    limit: int = Field(default=25, ge=1, le=200)


class AcquisitionPromotionWorkflow(BaseModel):
    schema_version: str = "gw2radar.acquisition_promotion_workflow.v1"
    filter: AcquisitionPromotionWorkflowFilter
    ready: bool
    readiness_ready: bool
    maturity_label: str
    overall_score: float
    coverage_status_counts: dict[str, int]
    queue_item_count: int
    filtered_item_count: int
    visible_items: list[AcquisitionPromotionQueueItem]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_operator_steps: list[str] = Field(default_factory=list)
    safety_boundary: list[str] = Field(default_factory=list)


def build_acquisition_promotion_workflow(
    session: Session,
    *,
    priority: str | None = None,
    item_type: str | None = None,
    limit: int = 25,
) -> AcquisitionPromotionWorkflow:
    filter_input = AcquisitionPromotionWorkflowFilter(priority=priority, item_type=item_type, limit=limit)
    readiness = build_acquisition_readiness_report(session)
    maturity = build_acquisition_maturity_report(session)
    coverage = build_evidence_coverage_map(session)
    queue = build_acquisition_promotion_queue(session)
    promotion_readiness = build_acquisition_promotion_readiness_report(session)

    filtered_items = [
        item
        for item in queue.items
        if (filter_input.priority is None or item.priority == filter_input.priority)
        and (filter_input.item_type is None or item.item_type == filter_input.item_type)
    ]
    visible_items = filtered_items[: filter_input.limit]
    return AcquisitionPromotionWorkflow(
        filter=filter_input,
        ready=promotion_readiness.ready and readiness.ready,
        readiness_ready=readiness.ready,
        maturity_label=maturity.maturity_label,
        overall_score=maturity.overall_score,
        coverage_status_counts=_coverage_status_counts(coverage.source_rows),
        queue_item_count=queue.item_count,
        filtered_item_count=len(filtered_items),
        visible_items=visible_items,
        blockers=[*_readiness_blocker_text(readiness.blockers), *promotion_readiness.blockers],
        warnings=[*readiness.recommendations, *promotion_readiness.warnings],
        next_operator_steps=_dedupe([*promotion_readiness.next_operator_steps, *queue.next_operator_steps]),
        safety_boundary=[
            "Workflow is read-only and does not persist KnowledgeRule records.",
            "Operators must preserve source attribution and summary-only source handling.",
            "No automatic trading, guaranteed returns, or private player data exposure is allowed.",
        ],
    )


def render_acquisition_promotion_workflow_markdown(workflow: AcquisitionPromotionWorkflow) -> str:
    lines = [
        "# Acquisition Promotion Operator Workflow",
        "",
        f"- schema_version: `{workflow.schema_version}`",
        f"- ready: `{str(workflow.ready).lower()}`",
        f"- readiness_ready: `{str(workflow.readiness_ready).lower()}`",
        f"- maturity_label: `{workflow.maturity_label}`",
        f"- overall_score: `{workflow.overall_score:.3f}`",
        f"- queue_item_count: `{workflow.queue_item_count}`",
        f"- filtered_item_count: `{workflow.filtered_item_count}`",
        f"- filter_priority: `{workflow.filter.priority or 'any'}`",
        f"- filter_item_type: `{workflow.filter.item_type or 'any'}`",
        "",
        "## Safety Boundary",
        "",
    ]
    lines.extend(f"- {note}" for note in workflow.safety_boundary)
    lines.extend(["", "## Coverage Status Counts", ""])
    if workflow.coverage_status_counts:
        lines.extend(f"- {key}: `{value}`" for key, value in sorted(workflow.coverage_status_counts.items()))
    else:
        lines.append("- none")
    lines.extend(["", "## Visible Queue Items", ""])
    lines.extend(
        [
            "| Priority | Type | Target | Title | Recommended Action |",
            "|---|---|---|---|---|",
        ]
    )
    for item in workflow.visible_items:
        target = item.source_id or item.evidence_id or item.rule_id or "n/a"
        lines.append(f"| {item.priority} | {item.item_type} | {target} | {item.title} | {item.recommended_action} |")
    lines.extend(["", "## Blockers", ""])
    lines.extend(f"- {item}" for item in workflow.blockers) if workflow.blockers else lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    lines.extend(f"- {item}" for item in workflow.warnings) if workflow.warnings else lines.append("- none")
    lines.extend(["", "## Next Operator Steps", ""])
    lines.extend(f"- {step}" for step in workflow.next_operator_steps) if workflow.next_operator_steps else lines.append(
        "- Continue normal reviewed source import and KB promotion cadence."
    )
    return "\n".join(lines) + "\n"


def _coverage_status_counts(source_rows: list) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in source_rows:
        counts[row.coverage_status] = counts.get(row.coverage_status, 0) + 1
    return counts


def _dedupe(items: list[str]) -> list[str]:
    deduped: list[str] = []
    for item in items:
        if item not in deduped:
            deduped.append(item)
    return deduped[:8]


def _readiness_blocker_text(blockers: list) -> list[str]:
    texts: list[str] = []
    for blocker in blockers:
        source = f" [{blocker.source_id}]" if blocker.source_id else ""
        texts.append(f"{blocker.severity}: {blocker.reason}{source} - {blocker.detail}")
    return texts
