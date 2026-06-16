from pydantic import BaseModel, Field

from gw2radar.kb.kb_models import KnowledgeReviewStatus, KnowledgeRule
from gw2radar.ontology.schemas import Action


class KnowledgeBackedExplanation(BaseModel):
    action_id: str
    rule_id: str
    rule_name: str
    recommendation: str
    explanation: str
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float


def explain_action_with_kb(action: Action, rules: list[KnowledgeRule]) -> list[KnowledgeBackedExplanation]:
    explanations: list[KnowledgeBackedExplanation] = []
    for rule in rules:
        if not _rule_matches_action(rule, action):
            continue
        explanations.append(
            KnowledgeBackedExplanation(
                action_id=action.id,
                rule_id=rule.rule_id,
                rule_name=rule.name,
                recommendation=rule.recommendation,
                explanation=rule.explanation_template,
                evidence_refs=rule.evidence_refs,
                confidence=rule.confidence,
            )
        )
    return explanations


def explain_actions_with_kb(actions: list[Action], rules: list[KnowledgeRule]) -> dict[str, list[KnowledgeBackedExplanation]]:
    return {action.id: explain_action_with_kb(action, rules) for action in actions}


def render_kb_explanation_section(explanations: dict[str, list[KnowledgeBackedExplanation]]) -> list[str]:
    lines = ["## Knowledge Base Explanations"]
    used = [item for action_items in explanations.values() for item in action_items]
    if not used:
        return [*lines, "- No reviewed KB explanations matched these recommendations."]
    for item in used:
        source_refs = ", ".join(item.evidence_refs) if item.evidence_refs else "none"
        lines.append(f"- {item.rule_name}: {item.recommendation}")
        lines.append(f"  - Applies to action: {item.action_id}")
        lines.append(f"  - Explanation: {item.explanation}")
        lines.append(f"  - KB confidence: {item.confidence:.2f}; source refs: {source_refs}")
    return lines


def _rule_matches_action(rule: KnowledgeRule, action: Action) -> bool:
    if not rule.enabled:
        return False
    if rule.review_status != KnowledgeReviewStatus.REVIEWED:
        return False
    if rule.action_type != action.action_type.value:
        return False
    linked_entities = _entities_from_condition(rule.condition)
    if linked_entities and action.target_entity_id not in linked_entities:
        return False
    return True


def _entities_from_condition(condition: str) -> list[str]:
    prefix = "article_links_any_entity:"
    if not condition.startswith(prefix):
        return []
    raw = condition[len(prefix) :]
    return [part.strip() for part in raw.split(",") if part.strip()]
