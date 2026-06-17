from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.acquisition.promotion_queue import AcquisitionPromotionQueueItem, build_acquisition_promotion_queue


class AcquisitionPromotionActionPlan(BaseModel):
    schema_version: str = "gw2radar.acquisition_promotion_action_plan.v1"
    item_id: str
    item_type: str
    priority: str
    target_id: str
    title: str
    checklist: list[str] = Field(default_factory=list)
    expected_evidence: list[str] = Field(default_factory=list)
    review_gates: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    completion_definition: str


class AcquisitionPromotionActionPlanBundle(BaseModel):
    schema_version: str = "gw2radar.acquisition_promotion_action_plan_bundle.v1"
    requested_item_id: str | None = None
    plan_count: int
    plans: list[AcquisitionPromotionActionPlan]


def build_acquisition_promotion_action_plans(
    session: Session,
    *,
    item_id: str | None = None,
    limit: int = 50,
) -> AcquisitionPromotionActionPlanBundle:
    queue = build_acquisition_promotion_queue(session)
    items = [item for item in queue.items if item_id is None or item.item_id == item_id]
    plans = [_plan_for_item(item) for item in items[:limit]]
    return AcquisitionPromotionActionPlanBundle(
        requested_item_id=item_id,
        plan_count=len(plans),
        plans=plans,
    )


def render_acquisition_promotion_action_plans_markdown(bundle: AcquisitionPromotionActionPlanBundle) -> str:
    lines = [
        "# Acquisition Promotion Action Plans",
        "",
        f"- schema_version: `{bundle.schema_version}`",
        f"- requested_item_id: `{bundle.requested_item_id or 'all'}`",
        f"- plan_count: `{bundle.plan_count}`",
        "",
    ]
    if not bundle.plans:
        lines.append("No action plans matched the request.")
        return "\n".join(lines) + "\n"
    for plan in bundle.plans:
        lines.extend(
            [
                f"## {plan.title}",
                "",
                f"- item_id: `{plan.item_id}`",
                f"- item_type: `{plan.item_type}`",
                f"- priority: `{plan.priority}`",
                f"- target_id: `{plan.target_id}`",
                "",
                "### Checklist",
                "",
            ]
        )
        lines.extend(f"- {item}" for item in plan.checklist)
        lines.extend(["", "### Expected Evidence", ""])
        lines.extend(f"- {item}" for item in plan.expected_evidence)
        lines.extend(["", "### Review Gates", ""])
        lines.extend(f"- {item}" for item in plan.review_gates)
        lines.extend(["", "### Forbidden Actions", ""])
        lines.extend(f"- {item}" for item in plan.forbidden_actions)
        lines.extend(["", f"Completion definition: {plan.completion_definition}", ""])
    return "\n".join(lines) + "\n"


def _plan_for_item(item: AcquisitionPromotionQueueItem) -> AcquisitionPromotionActionPlan:
    checklist, expected_evidence, review_gates, completion = _type_guidance(item)
    return AcquisitionPromotionActionPlan(
        item_id=item.item_id,
        item_type=item.item_type,
        priority=item.priority,
        target_id=item.source_id or item.evidence_id or item.rule_id or "n/a",
        title=item.title,
        checklist=checklist,
        expected_evidence=expected_evidence,
        review_gates=review_gates,
        forbidden_actions=[
            "Do not copy full source text into KB articles or paid reports.",
            "Do not enable a KnowledgeRule without reviewer confirmation.",
            "Do not include private account data in public KB or report artifacts.",
            "Do not frame market guidance as guaranteed profit or automated trading advice.",
        ],
        completion_definition=completion,
    )


def _type_guidance(item: AcquisitionPromotionQueueItem) -> tuple[list[str], list[str], list[str], str]:
    if item.item_type == "source_needs_raw_evidence":
        return (
            [
                "Run the matching acquisition adapter or create a manual summary evidence record.",
                "Confirm the source policy allows summary/reference use.",
                "Verify payload_ref or summary avoids full-text copying.",
            ],
            ["RawEvidence row linked to the acquisition source.", "Payload hash or payload_ref for traceability."],
            ["Source remains enabled and non-deprecated.", "Evidence contains no secrets or private player payload."],
            "The source has at least one safe RawEvidence row.",
        )
    if item.item_type == "source_needs_kb_article":
        return (
            [
                "Create or link a reviewed KB article for the source.",
                "Set source_refs_json to the acquisition source id.",
                "Keep article body summary-only and attribution-forward.",
            ],
            ["Reviewed KnowledgeArticle row.", "Source reference to the acquisition source."],
            ["Article review_status is reviewed.", "Article contains no unsupported claims."],
            "A reviewed KB article references the acquisition source.",
        )
    if item.item_type == "raw_evidence_needs_rule_candidate":
        return (
            [
                "Check whether evidence supports a durable recommendation rule.",
                "Distill a disabled KnowledgeRule candidate when appropriate.",
                "Attach raw evidence ids to evidence_refs.",
            ],
            ["Disabled KnowledgeRule candidate.", "Evidence refs pointing to RawEvidence ids."],
            ["Rule review_status is reviewed before any enable step.", "Enabled remains false until a separate gate."],
            "A disabled, reviewed rule candidate references the raw evidence.",
        )
    if item.item_type == "rule_needs_raw_evidence":
        return (
            [
                "Find the raw evidence that supports the existing rule.",
                "Replace document-only refs with RawEvidence ids or add RawEvidence ids alongside them.",
                "Keep the rule disabled until the evidence chain is complete.",
            ],
            ["KnowledgeRule evidence_refs include at least one RawEvidence id."],
            ["Evidence chain can be traced from rule to raw evidence to acquisition source."],
            "The rule cites at least one RawEvidence id.",
        )
    return (
        [
            "Inspect the orphan raw evidence source_id.",
            "Restore the missing source registry row or migrate evidence to a valid source.",
            "Rebuild coverage and promotion readiness after repair.",
        ],
        ["Valid AcquisitionSource row for the evidence source_id."],
        ["No orphan raw evidence remains for this evidence id."],
        "The raw evidence is linked to a valid acquisition source.",
    )
