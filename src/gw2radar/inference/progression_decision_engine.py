from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.db.models import MarketSnapshotModel
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
    execution_risk: str | None = None
    liquidity_reason: str | None = None


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
    session: Session | None = None,
) -> ProgressionDecisionResult:
    actions = graph.actions_for_goal(goal_id) or generate_actions(graph, goal_id)
    candidates = [_candidate_for_action(action, rules, session=session) for action in actions]
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


def _latest_market_liquidity(entity_id: str, session: Session | None) -> tuple[float, float, str | None]:
    if session is None:
        return (1.0, 0.0, None)
    rows = (
        session.query(MarketSnapshotModel)
        .filter(MarketSnapshotModel.item_id == entity_id)
        .order_by(MarketSnapshotModel.observed_at.desc())
        .limit(5)
        .all()
    )
    if not rows:
        return (0.0, 0.0, "No market price snapshots available.")
    latest = rows[0]
    volume = latest.volume or 0
    liquidity = min(volume / 10000, 1.0)
    average = sum(r.sell_price_copper for r in rows) / len(rows)
    if average:
        spread = sum(abs(r.sell_price_copper - average) for r in rows) / len(rows)
        volatility = min(spread / average, 1.0)
    else:
        volatility = 0.0
    return (round(liquidity, 3), round(volatility, 3), None)


def _market_execution_risk(action: Action, session: Session | None = None) -> tuple[str | None, str | None]:
    at = action.action_type.value
    if action.target_entity_id:
        liquidity, volatility, snap_err = _latest_market_liquidity(action.target_entity_id, session)
    else:
        liquidity, volatility, snap_err = 1.0, 0.0, None
    if at == "buy":
        if snap_err:
            return ("price_volatility_risk", snap_err)
        if volatility > 0.3:
            return ("price_volatility_risk", f"High volatility ({volatility:.2f}); consider observing before committing.")
        return ("timing_risk", "Buy timing depends on market price; review current snapshots before committing.")
    if at == "sell_surplus":
        if snap_err:
            return ("liquidity_risk", snap_err)
        if liquidity < 0.3:
            return ("liquidity_risk", f"Low liquidity ({liquidity:.2f}); selling may take time at a fair price.")
        if volatility > 0.3:
            return ("price_volatility_risk", f"Price is volatile ({volatility:.2f}); review trend before listing.")
        return ("timing_risk", "Surplus sell is price-sensitive; review trend before listing.")
    if at == "watch_price":
        return (None, None)
    if at == "exchange":
        if snap_err:
            return ("spread_risk", snap_err)
        if liquidity < 0.3:
            return ("liquidity_risk", f"Low liquidity ({liquidity:.2f}); exchange may have wide spread.")
        return ("spread_risk", "Exchange spread may reduce effective value; compare buy/sell prices.")
    if at == "craft":
        return ("material_cost_risk", "Crafting cost depends on current material prices; verify before committing.")
    if at in {"do_daily", "do_weekly", "farm", "complete_achievement", "complete_collection_step"}:
        return (None, None)
    return (None, None)


def _candidate_for_action(action: Action, rules: list[KnowledgeRule], *, session: Session | None = None) -> ProgressionDecisionCandidate:
    explanations = explain_action_with_kb(action, rules)
    matched_rules = [_rule_by_id(rules, explanation.rule_id) for explanation in explanations]
    reviewed_rules = [rule for rule in matched_rules if rule is not None and _reviewed_enabled(rule)]
    kb_delta = min(0.25, sum(max(0.0, rule.priority_delta) for rule in reviewed_rules))
    final_score = min(1.0, round(action.priority_score + kb_delta, 4))
    warnings = _warnings_for_action(action, explanations)
    execution_risk, liquidity_reason = _market_execution_risk(action, session=session)
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
        execution_risk=execution_risk,
        liquidity_reason=liquidity_reason,
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
