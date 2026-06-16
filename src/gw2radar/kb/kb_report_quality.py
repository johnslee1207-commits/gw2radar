from pydantic import BaseModel, Field

from gw2radar.kb.kb_explanation import KnowledgeBackedExplanation, explain_actions_with_kb
from gw2radar.kb.kb_models import KnowledgeReviewStatus, KnowledgeRule
from gw2radar.ontology.schemas import Action


LOW_CONFIDENCE_EXPLANATION_THRESHOLD = 0.7


class KnowledgeReportQualityScore(BaseModel):
    total_actions: int
    explained_actions: int
    unexplained_action_ids: list[str] = Field(default_factory=list)
    matched_rule_count: int
    reviewed_enabled_rule_count: int
    explanation_coverage_percent: float
    average_explanation_confidence: float
    low_confidence_explanation_count: int
    quality_label: str
    warnings: list[str] = Field(default_factory=list)


def score_kb_report_quality(
    actions: list[Action],
    rules: list[KnowledgeRule],
    explanations: dict[str, list[KnowledgeBackedExplanation]] | None = None,
) -> KnowledgeReportQualityScore:
    explanations = explanations or explain_actions_with_kb(actions, rules)
    total_actions = len(actions)
    explained_action_ids = [action_id for action_id, items in explanations.items() if items]
    unexplained_action_ids = [action.id for action in actions if not explanations.get(action.id)]
    matched = [item for items in explanations.values() for item in items]
    confidence_values = [item.confidence for item in matched]
    coverage = (len(explained_action_ids) / total_actions * 100.0) if total_actions else 100.0
    average_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
    low_confidence_count = sum(
        1 for value in confidence_values if value < LOW_CONFIDENCE_EXPLANATION_THRESHOLD
    )
    warnings = _build_warnings(total_actions, unexplained_action_ids, low_confidence_count, matched)
    return KnowledgeReportQualityScore(
        total_actions=total_actions,
        explained_actions=len(explained_action_ids),
        unexplained_action_ids=unexplained_action_ids,
        matched_rule_count=len(matched),
        reviewed_enabled_rule_count=_count_reviewed_enabled_rules(rules),
        explanation_coverage_percent=round(coverage, 2),
        average_explanation_confidence=round(average_confidence, 2),
        low_confidence_explanation_count=low_confidence_count,
        quality_label=_quality_label(coverage, average_confidence, low_confidence_count),
        warnings=warnings,
    )


def render_kb_quality_section(score: KnowledgeReportQualityScore) -> list[str]:
    lines = [
        "## Knowledge Base Quality",
        f"- Explanation coverage: {score.explanation_coverage_percent:.2f}%",
        f"- Explained actions: {score.explained_actions}/{score.total_actions}",
        f"- Matched reviewed rules: {score.matched_rule_count}",
        f"- Average KB confidence: {score.average_explanation_confidence:.2f}",
        f"- Quality label: {score.quality_label}",
    ]
    if score.unexplained_action_ids:
        lines.append("- Unexplained actions: " + ", ".join(score.unexplained_action_ids))
    if score.warnings:
        lines.append("- Warnings:")
        lines.extend(f"  - {warning}" for warning in score.warnings)
    else:
        lines.append("- Warnings: none")
    return lines


def _count_reviewed_enabled_rules(rules: list[KnowledgeRule]) -> int:
    return sum(1 for rule in rules if rule.enabled and rule.review_status == KnowledgeReviewStatus.REVIEWED)


def _quality_label(coverage: float, average_confidence: float, low_confidence_count: int) -> str:
    if coverage >= 80.0 and average_confidence >= 0.8 and low_confidence_count == 0:
        return "strong"
    if coverage >= 50.0 and average_confidence >= 0.65:
        return "moderate"
    return "needs_review"


def _build_warnings(
    total_actions: int,
    unexplained_action_ids: list[str],
    low_confidence_count: int,
    matched: list[KnowledgeBackedExplanation],
) -> list[str]:
    warnings: list[str] = []
    if total_actions == 0:
        warnings.append("No actions were available for KB quality scoring.")
    if unexplained_action_ids:
        warnings.append("Some recommendations have no reviewed KB explanation.")
    if not matched:
        warnings.append("No reviewed KB rules matched this report.")
    if low_confidence_count:
        warnings.append("Some KB explanations are below the confidence threshold.")
    return warnings
