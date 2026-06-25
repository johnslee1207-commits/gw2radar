from __future__ import annotations

from uuid import uuid4

from gw2radar.player_os.intent.constraint_extractor import constraints_to_dict, extract_constraints
from gw2radar.player_os.intent.models import PlanDiff, PlayerPlan, WhatIfResult


def revise_plan(plan: PlayerPlan, raw_revision_text: str, constraints_delta: dict | None = None) -> tuple[PlayerPlan, PlanDiff]:
    extracted = constraints_to_dict(extract_constraints(raw_revision_text, f"{plan.intent_id}:revision"))
    changed = {**extracted, **(constraints_delta or {})}
    revised_constraints = {**plan.constraints, **changed}
    revised = plan.model_copy(deep=True)
    revised.plan_id = f"plan-{uuid4().hex[:12]}"
    revised.version = plan.version + 1
    revised.constraints = revised_constraints
    revised.focus = _focus_with_constraints(plan.focus, changed)
    if changed.get("daily_time_limit"):
        revised.warnings = [*revised.warnings, f"Plan rebalanced for daily time limit {changed['daily_time_limit']}."]
    if changed.get("avoid_modes"):
        revised.warnings = [*revised.warnings, f"Avoided modes are treated as constraints: {', '.join(changed['avoid_modes'])}."]
    if changed.get("budget_gold_limit") is not None:
        revised.warnings = [*revised.warnings, f"Budget cap set to {changed['budget_gold_limit']} gold; expensive actions should be deferred."]
    diff = PlanDiff(
        previous_plan_id=plan.plan_id,
        revised_plan_id=revised.plan_id,
        changed_constraints=changed,
        added_warnings=[warning for warning in revised.warnings if warning not in plan.warnings],
        old_focus=plan.focus,
        new_focus=revised.focus,
        summary="Plan revised by updating constraints and preserving evidence, assumptions, and safety boundaries.",
    )
    return revised, diff


def evaluate_what_if(plan: PlayerPlan, raw_text: str, constraints_delta: dict | None = None) -> WhatIfResult:
    extracted = constraints_to_dict(extract_constraints(raw_text, f"{plan.intent_id}:what-if"))
    changed = {**extracted, **(constraints_delta or {})}
    feasibility = "feasible_with_review" if changed else "needs_clarification"
    warnings = []
    if "avoid_modes" in changed:
        warnings.append("Avoid-mode feasibility depends on reviewed route and achievement evidence.")
    if "budget_gold_limit" in changed:
        warnings.append("Cost estimates depend on price freshness and account holding coverage.")
    return WhatIfResult(
        plan_id=plan.plan_id,
        changed_constraints=changed,
        plan_delta="Prioritize actions that satisfy the changed constraints; preserve evidence and assumptions.",
        cost_delta="Likely lower spend if cheap/budget constraints are present; exact value requires refreshed market evidence.",
        time_delta=f"Plan is constrained by {changed.get('daily_time_limit', 'the requested schedule')}.",
        feasibility=feasibility,
        warnings=warnings,
    )


def _focus_with_constraints(focus: str, changed: dict) -> str:
    notes = []
    if changed.get("daily_time_limit"):
        notes.append(f"{changed['daily_time_limit']} per day")
    if changed.get("avoid_modes"):
        notes.append("avoid " + ", ".join(changed["avoid_modes"]))
    if changed.get("budget_gold_limit") is not None:
        notes.append(f"budget {changed['budget_gold_limit']}g")
    if not notes:
        return focus
    return f"{focus} Revised for: {', '.join(notes)}."
