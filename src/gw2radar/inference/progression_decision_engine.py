from pydantic import BaseModel, Field

from gw2radar.graph.graph_query import GraphData
from gw2radar.inference.action_generator import generate_actions
from gw2radar.kb.kb_explanation import KnowledgeBackedExplanation, explain_action_with_kb
from gw2radar.kb.kb_models import KnowledgeReviewStatus, KnowledgeRule
from gw2radar.ontology.schemas import Action


class ProgressionDecisionCandidate(BaseModel):
    schema_version: str = "gw2radar.progression_decision_candidate.v1"
    rank: int
    action_id: str
    action_type: str
    title: str
    target_entity_id: str | None = None
    target_goal_id: str | None = None
    base_score: float
    kb_score_delta: float
    final_score: float
    recommendation_strength: str
    urgency: str
    reason_codes: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    kb_explanations: list[KnowledgeBackedExplanation] = Field(default_factory=list)
    action: dict
    manual_action_boundary: str = "Candidate is informational only and requires manual player review."
    no_auto_execution: bool = True


class ProgressionDecisionResult(BaseModel):
    schema_version: str = "gw2radar.progression_decision_result.v1"
    goal_id: str
    top_k: int
    generated_action_count: int
    returned_candidate_count: int
    candidates: list[ProgressionDecisionCandidate]
    scoring_contract: dict
    safety_boundaries: list[str]
    deferred_capabilities: list[str]


def build_progression_decisions(
    graph: GraphData,
    goal_id: str,
    rules: list[KnowledgeRule],
    *,
    top_k: int = 5,
) -> ProgressionDecisionResult:
    actions = graph.actions_for_goal(goal_id) or generate_actions(graph, goal_id)
    candidates = [_candidate_for_action(action, rules) for action in actions]
    candidates.sort(key=lambda item: (item.final_score, item.base_score, item.action_id), reverse=True)
    limited = candidates[: max(1, min(top_k, 25))]
    ranked = [candidate.model_copy(update={"rank": index}) for index, candidate in enumerate(limited, start=1)]
    return ProgressionDecisionResult(
        goal_id=goal_id,
        top_k=max(1, min(top_k, 25)),
        generated_action_count=len(actions),
        returned_candidate_count=len(ranked),
        candidates=ranked,
        scoring_contract={
            "base_score_source": "gw2radar.inference.action_ranker plus evidence-quality adjustments",
            "kb_score_delta_source": "reviewed enabled KnowledgeRule.priority_delta only",
            "max_kb_delta_per_action": 0.25,
            "score_cap": 1.0,
            "unreviewed_rule_policy": "ignored_for_score_and_explanation",
        },
        safety_boundaries=_safety_boundaries(),
        deferred_capabilities=[
            "automatic trading",
            "automatic gameplay execution",
            "profit guarantees",
            "real-time autonomous replanning",
        ],
    )


def _candidate_for_action(action: Action, rules: list[KnowledgeRule]) -> ProgressionDecisionCandidate:
    explanations = explain_action_with_kb(action, rules)
    matched_rules = [_rule_by_id(rules, explanation.rule_id) for explanation in explanations]
    reviewed_rules = [rule for rule in matched_rules if rule is not None and _reviewed_enabled(rule)]
    kb_delta = min(0.25, sum(max(0.0, rule.priority_delta) for rule in reviewed_rules))
    final_score = min(1.0, round(action.priority_score + kb_delta, 4))
    warnings = _warnings_for_action(action, explanations)
    return ProgressionDecisionCandidate(
        rank=0,
        action_id=action.id,
        action_type=action.action_type.value,
        title=action.title,
        target_entity_id=action.target_entity_id,
        target_goal_id=action.target_goal_id,
        base_score=round(action.priority_score, 4),
        kb_score_delta=round(kb_delta, 4),
        final_score=final_score,
        recommendation_strength=_recommendation_strength(action, explanations, final_score),
        urgency=action.urgency,
        reason_codes=list(dict.fromkeys([*action.reason_codes, *_kb_reason_codes(explanations)])),
        assumptions=_assumptions_for_action(action),
        warnings=warnings,
        evidence_refs=list(dict.fromkeys([*action.evidence_refs, *_kb_evidence_refs(explanations)])),
        kb_explanations=explanations,
        action=action.model_dump(mode="json"),
    )


def _recommendation_strength(
    action: Action,
    explanations: list[KnowledgeBackedExplanation],
    final_score: float,
) -> str:
    if action.constraints.get("evidence_confidence") == "low" or action.constraints.get("evidence_stale") is True:
        return "review_only"
    if final_score >= 0.85 and explanations:
        return "strong_review_candidate"
    if final_score >= 0.7:
        return "standard_review_candidate"
    return "review_only"


def _warnings_for_action(action: Action, explanations: list[KnowledgeBackedExplanation]) -> list[str]:
    warnings: list[str] = []
    if not explanations:
        warnings.append("No reviewed enabled KB explanation matched this action.")
    if action.constraints.get("evidence_confidence") == "low":
        warnings.append("Evidence confidence is low; verify source freshness before acting.")
    if action.constraints.get("evidence_stale") is True:
        warnings.append("Evidence may be stale; refresh sources before high-impact decisions.")
    if action.action_type.value in {"buy", "sell_surplus", "watch_price"}:
        warnings.append("Market-facing recommendation is a manual review candidate, not trading advice.")
    return warnings


def _assumptions_for_action(action: Action) -> list[str]:
    assumptions = [
        "Player account state and market context are represented by the current local graph snapshot.",
        "The player manually reviews and performs any in-game or market action.",
    ]
    if not action.preconditions:
        assumptions.append("No explicit preconditions were attached to this candidate.")
    return assumptions


def _kb_reason_codes(explanations: list[KnowledgeBackedExplanation]) -> list[str]:
    if not explanations:
        return ["missing_kb_explanation"]
    return ["reviewed_kb_explanation"]


def _kb_evidence_refs(explanations: list[KnowledgeBackedExplanation]) -> list[str]:
    refs: list[str] = []
    for explanation in explanations:
        refs.extend(explanation.evidence_refs)
    return refs


def _rule_by_id(rules: list[KnowledgeRule], rule_id: str) -> KnowledgeRule | None:
    return next((rule for rule in rules if rule.rule_id == rule_id), None)


def _reviewed_enabled(rule: KnowledgeRule) -> bool:
    return rule.enabled and rule.review_status == KnowledgeReviewStatus.REVIEWED


def _safety_boundaries() -> list[str]:
    return [
        "Decision candidates are informational and require manual player review.",
        "The engine never buys, sells, trades, changes gear, completes achievements, or controls gameplay.",
        "Only reviewed enabled KnowledgeRule records can influence KB score deltas.",
        "Missing facts remain assumptions or warnings; no guaranteed outcome is produced.",
    ]
