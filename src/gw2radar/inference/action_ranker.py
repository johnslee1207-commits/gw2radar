from gw2radar.ontology.action_types import ActionType


def rank_action(
    action_type: ActionType,
    *,
    advances_goal: bool = False,
    resolves_missing_requirement: bool = False,
    is_time_gated: bool = False,
    estimated_minutes: int | None = None,
    protects_required_material: bool = False,
) -> float:
    score = 0.5
    if advances_goal:
        score += 0.2
    if resolves_missing_requirement:
        score += 0.2
    if is_time_gated or action_type in {ActionType.DO_DAILY, ActionType.DO_WEEKLY}:
        score += 0.1
    if estimated_minutes is not None and estimated_minutes <= 30:
        score += 0.05
    if protects_required_material:
        score += 0.1
    return min(score, 1.0)
