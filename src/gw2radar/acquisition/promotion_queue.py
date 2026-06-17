from collections import Counter

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.acquisition.coverage import build_evidence_coverage_map
from gw2radar.db.models import AcquisitionSourceModel, KnowledgeRuleModel, RawEvidenceModel


class AcquisitionPromotionQueueItem(BaseModel):
    item_id: str
    item_type: str
    priority: str
    source_id: str | None = None
    evidence_id: str | None = None
    rule_id: str | None = None
    title: str
    summary: str
    recommended_action: str
    safety_notes: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class AcquisitionPromotionQueue(BaseModel):
    schema_version: str = "gw2radar.acquisition_promotion_queue.v1"
    item_count: int
    counts_by_type: dict[str, int]
    items: list[AcquisitionPromotionQueueItem]
    next_operator_steps: list[str] = Field(default_factory=list)


def build_acquisition_promotion_queue(session: Session) -> AcquisitionPromotionQueue:
    coverage = build_evidence_coverage_map(session)
    sources = {source.source_id: source for source in session.query(AcquisitionSourceModel).all()}
    evidence = session.query(RawEvidenceModel).order_by(RawEvidenceModel.evidence_id).all()
    evidence_by_source: dict[str, list[RawEvidenceModel]] = {}
    evidence_by_id = {item.evidence_id: item for item in evidence}
    for item in evidence:
        evidence_by_source.setdefault(item.source_id, []).append(item)

    items: list[AcquisitionPromotionQueueItem] = []
    for row in coverage.source_rows:
        source = sources.get(row.source_id)
        if row.raw_evidence_count == 0:
            items.append(
                _item(
                    item_type="source_needs_raw_evidence",
                    priority=_source_priority(source),
                    source_id=row.source_id,
                    title=f"Import raw evidence for {row.name}",
                    summary=f"Acquisition source `{row.source_id}` is registered but has no raw evidence rows.",
                    recommended_action=(
                        "Run the matching safe adapter or add a manual summary evidence record before using this source "
                        "for KB articles or report rules."
                    ),
                )
            )
        if row.raw_evidence_count > 0 and row.kb_article_count == 0:
            items.append(
                _item(
                    item_type="source_needs_kb_article",
                    priority="P2",
                    source_id=row.source_id,
                    title=f"Create reviewed KB article for {row.name}",
                    summary=(
                        f"Raw evidence exists for `{row.source_id}` but no reviewed KB article references this source."
                    ),
                    recommended_action=(
                        "Create a summary-only KB article with source_refs_json pointing to the acquisition source."
                    ),
                    evidence_refs=[item.evidence_id for item in evidence_by_source.get(row.source_id, [])[:5]],
                )
            )
        if row.raw_evidence_count > 0 and row.knowledge_rule_count == 0:
            items.append(
                _item(
                    item_type="raw_evidence_needs_rule_candidate",
                    priority="P3",
                    source_id=row.source_id,
                    title=f"Review rule candidate opportunity for {row.name}",
                    summary=(
                        f"Evidence for `{row.source_id}` is not yet connected to any KnowledgeRule evidence refs."
                    ),
                    recommended_action=(
                        "Distill a disabled KnowledgeRule candidate only after the source summary is reviewed."
                    ),
                    evidence_refs=[item.evidence_id for item in evidence_by_source.get(row.source_id, [])[:5]],
                )
            )

    for evidence_id in coverage.orphan_raw_evidence_ids:
        item = evidence_by_id.get(evidence_id)
        items.append(
            _item(
                item_type="orphan_raw_evidence",
                priority="P1",
                source_id=item.source_id if item else None,
                evidence_id=evidence_id,
                title=f"Resolve orphan raw evidence {evidence_id}",
                summary="Raw evidence points at a source_id that is not present in the acquisition registry.",
                recommended_action=(
                    "Restore the missing source registry row or migrate the evidence to a valid source before promotion."
                ),
                evidence_refs=[evidence_id],
            )
        )

    for rule_id in coverage.rule_ids_without_raw_evidence:
        rule = session.get(KnowledgeRuleModel, rule_id)
        items.append(
            _item(
                item_type="rule_needs_raw_evidence",
                priority="P1",
                rule_id=rule_id,
                title=f"Attach raw evidence to rule {rule_id}",
                summary="KnowledgeRule cites evidence refs, but none of those refs match raw evidence rows.",
                recommended_action=(
                    "Attach at least one raw evidence id or keep the rule disabled until the evidence chain is complete."
                ),
                evidence_refs=list((rule.evidence_refs_json if rule else []) or []),
            )
        )

    items = sorted(items, key=lambda item: (_priority_rank(item.priority), item.item_type, item.item_id))
    counts = dict(Counter(item.item_type for item in items))
    return AcquisitionPromotionQueue(
        item_count=len(items),
        counts_by_type=counts,
        items=items,
        next_operator_steps=_next_operator_steps(counts),
    )


def render_acquisition_promotion_queue_markdown(queue: AcquisitionPromotionQueue) -> str:
    lines = [
        "# Acquisition Evidence Promotion Queue",
        "",
        f"- schema_version: `{queue.schema_version}`",
        f"- item_count: `{queue.item_count}`",
        "",
        "## Safety Boundary",
        "",
        "- This queue is read-only and does not persist, enable, or promote KnowledgeRule records.",
        "- Operators must keep generated content summary-only and preserve source attribution.",
        "- No automatic trading, guaranteed returns, or private-account data exposure is allowed.",
        "",
        "## Queue Items",
        "",
        "| Priority | Type | Target | Title | Recommended Action | Evidence Refs |",
        "|---|---|---|---|---|---|",
    ]
    for item in queue.items:
        target = item.source_id or item.evidence_id or item.rule_id or "n/a"
        refs = "; ".join(item.evidence_refs) if item.evidence_refs else "none"
        lines.append(
            f"| {item.priority} | {item.item_type} | {target} | {item.title} | "
            f"{item.recommended_action} | {refs} |"
        )
    lines.extend(["", "## Next Operator Steps", ""])
    if queue.next_operator_steps:
        lines.extend(f"- {step}" for step in queue.next_operator_steps)
    else:
        lines.append("- Maintain normal acquisition review and patch freshness cadence.")
    return "\n".join(lines) + "\n"


def _item(
    *,
    item_type: str,
    priority: str,
    title: str,
    summary: str,
    recommended_action: str,
    source_id: str | None = None,
    evidence_id: str | None = None,
    rule_id: str | None = None,
    evidence_refs: list[str] | None = None,
) -> AcquisitionPromotionQueueItem:
    target = source_id or evidence_id or rule_id or "global"
    return AcquisitionPromotionQueueItem(
        item_id=f"promotion:{item_type}:{target}",
        item_type=item_type,
        priority=priority,
        source_id=source_id,
        evidence_id=evidence_id,
        rule_id=rule_id,
        title=title,
        summary=summary,
        recommended_action=recommended_action,
        safety_notes=[
            "Manual review is required before persistence or enablement.",
            "Use summaries and references; do not copy full source text.",
            "Recommendations must not imply automated trading or guaranteed profit.",
        ],
        evidence_refs=evidence_refs or [],
    )


def _source_priority(source: AcquisitionSourceModel | None) -> str:
    if source is None:
        return "P2"
    if source.source_type in {"official_api_public", "downloaded_pdf", "official_news"}:
        return "P1"
    return "P2"


def _priority_rank(priority: str) -> int:
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}
    return order.get(priority, 9)


def _next_operator_steps(counts: dict[str, int]) -> list[str]:
    steps: list[str] = []
    if counts.get("orphan_raw_evidence"):
        steps.append("Resolve orphan raw evidence before promoting any dependent KB article or rule.")
    if counts.get("rule_needs_raw_evidence"):
        steps.append("Attach raw evidence ids to existing rules or keep them disabled.")
    if counts.get("source_needs_raw_evidence"):
        steps.append("Run source adapters or add manual summaries for registered sources without raw evidence.")
    if counts.get("source_needs_kb_article"):
        steps.append("Create reviewed KB articles for evidence-backed sources.")
    if counts.get("raw_evidence_needs_rule_candidate"):
        steps.append("Distill disabled KnowledgeRule candidates from reviewed summary evidence.")
    return steps[:5]
