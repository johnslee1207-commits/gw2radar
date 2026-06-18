from pydantic import BaseModel, Field

from gw2radar.graph.graph_query import GraphData
from gw2radar.inference.action_generator import generate_actions
from gw2radar.inference.goal_gap import calculate_goal_gap
from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.entity_types import EntityType


DEFAULT_GOAL_ID = "gw2:goal:aurora"


class ReadinessDimension(BaseModel):
    dimension_id: str
    label: str
    score: int = Field(ge=0, le=100)
    status: str
    evidence: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class ReturnerReadinessReport(BaseModel):
    schema_version: str = "gw2radar.returner_readiness.v1"
    goal_id: str
    goal_name: str
    overall_score: int = Field(ge=0, le=100)
    overall_status: str
    dimensions: list[ReadinessDimension]
    what_to_do_first: list[str]
    goals_to_delay: list[str]
    safe_goals_to_start: list[str]
    data_freshness: str
    safety_boundaries: list[str]
    assumptions: list[str]


def build_returner_readiness_report(graph: GraphData, goal_id: str = DEFAULT_GOAL_ID) -> ReturnerReadinessReport:
    gap = calculate_goal_gap(graph, goal_id)
    actions = graph.actions_for_goal(goal_id) or generate_actions(graph, goal_id)
    dimensions = [
        _travel_dimension(graph),
        _combat_dimension(graph),
        _progression_dimension(gap),
        _legendary_dimension(gap, actions),
        _group_dimension(graph),
    ]
    overall_score = round(sum(item.score for item in dimensions) / len(dimensions)) if dimensions else 0
    return ReturnerReadinessReport(
        goal_id=goal_id,
        goal_name=gap.goal_name,
        overall_score=overall_score,
        overall_status=_status_for_score(overall_score),
        dimensions=dimensions,
        what_to_do_first=_first_actions(actions),
        goals_to_delay=_goals_to_delay(gap, dimensions),
        safe_goals_to_start=_safe_goals(dimensions, gap.progress_percent),
        data_freshness=_data_freshness(graph),
        safety_boundaries=[
            "Recommendations are planning guidance only.",
            "No gameplay automation is performed.",
            "No automatic trading, crafting, chat, or character control is performed.",
            "Missing account facts are marked as assumptions instead of invented.",
        ],
        assumptions=_report_assumptions(dimensions),
    )


def render_returner_readiness_markdown(report: ReturnerReadinessReport) -> str:
    lines = [
        "# Returner Readiness Report",
        "",
        f"Goal: {report.goal_name}",
        f"Overall score: {report.overall_score}/100",
        f"Overall status: {report.overall_status}",
        "",
        "## Readiness Scores",
    ]
    for dimension in report.dimensions:
        lines.extend(
            [
                f"- {dimension.label}: {dimension.score}/100 ({dimension.status})",
                *[f"  - Blocker: {blocker}" for blocker in dimension.blockers],
                *[f"  - Action: {action}" for action in dimension.recommended_actions],
                *[f"  - Assumption: {assumption}" for assumption in dimension.assumptions],
            ]
        )
    lines.extend(
        [
            "",
            "## What To Do First",
            *[f"- {item}" for item in report.what_to_do_first],
            "",
            "## Goals To Delay",
            *[f"- {item}" for item in report.goals_to_delay],
            "",
            "## Safe Goals To Start",
            *[f"- {item}" for item in report.safe_goals_to_start],
            "",
            "## Data Freshness",
            f"- {report.data_freshness}",
            "",
            "## Safety Boundaries",
            *[f"- {item}" for item in report.safety_boundaries],
        ]
    )
    return "\n".join(lines) + "\n"


def _travel_dimension(graph: GraphData) -> ReadinessDimension:
    has_private_state = bool(graph.player_state)
    score = 58 if has_private_state else 35
    return ReadinessDimension(
        dimension_id="travel",
        label="Travel",
        score=score,
        status=_status_for_score(score),
        evidence=["private player state present" if has_private_state else "no private player state"],
        blockers=[],
        recommended_actions=["Confirm mounts, gliding, and map access manually before long farming routes."],
        assumptions=[
            "The current graph does not expose detailed mount, gliding, waypoint, or map-completion facts."
        ],
    )


def _combat_dimension(graph: GraphData) -> ReadinessDimension:
    has_account = graph.account_id is not None
    score = 54 if has_account else 30
    return ReadinessDimension(
        dimension_id="combat",
        label="Combat",
        score=score,
        status=_status_for_score(score),
        evidence=["account identity present" if has_account else "no account identity"],
        blockers=["No character gear baseline is available in the returner graph."],
        recommended_actions=["Use Build Fit Advisor before entering fractals, strikes, raids, or WvW."],
        assumptions=["Playable character, gear baseline, and role readiness require manual or build-fit confirmation."],
    )


def _progression_dimension(gap) -> ReadinessDimension:
    missing_achievements = [item.name for item in gap.missing_requirements if item.entity_type == EntityType.ACHIEVEMENT]
    score = max(25, round(gap.progress_percent))
    return ReadinessDimension(
        dimension_id="progression",
        label="Progression",
        score=score,
        status=_status_for_score(score),
        evidence=[f"{gap.progress_percent:.0f}% of active goal requirements completed"],
        blockers=missing_achievements,
        recommended_actions=["Clear missing collection or achievement steps before high-cost material spending."]
        if missing_achievements
        else ["Continue current progression path."],
        assumptions=["Story unlocks and mastery details are not fully modeled in the current graph."],
    )


def _legendary_dimension(gap, actions) -> ReadinessDimension:
    missing_count = len(gap.missing_requirements)
    daily_actions = [action.title for action in actions if action.action_type == ActionType.DO_DAILY]
    score = max(20, min(85, round(gap.progress_percent - (missing_count * 5) + (len(daily_actions) * 6))))
    blockers = [item.name for item in gap.missing_requirements]
    return ReadinessDimension(
        dimension_id="legendary",
        label="Legendary",
        score=score,
        status=_status_for_score(score),
        evidence=[f"{missing_count} missing requirements for {gap.goal_name}"],
        blockers=blockers,
        recommended_actions=(daily_actions or ["Generate actions for the active legendary goal."])[:3],
        assumptions=["Cost and route speed depend on fresh market snapshots and manual player choices."],
    )


def _group_dimension(graph: GraphData) -> ReadinessDimension:
    group_tasks = [
        entity.canonical_name
        for entity in graph.entities.values()
        if entity.properties.get("requires_group") is True
    ]
    score = 42 if group_tasks else 50
    return ReadinessDimension(
        dimension_id="group_pve",
        label="Group PvE",
        score=score,
        status=_status_for_score(score),
        evidence=group_tasks or ["no group-gated task evidence in active graph"],
        blockers=group_tasks,
        recommended_actions=["Treat fractal, strike, raid, and WvW readiness as manual review until Build Fit is checked."],
        assumptions=["Agony resistance, role coverage, encounter experience, and squad requirements are not modeled here."],
    )


def _first_actions(actions) -> list[str]:
    titles = [action.title for action in sorted(actions, key=lambda item: item.priority_score, reverse=True)]
    return (titles or ["Connect and sync account data.", "Load active goal gap.", "Generate a short recovery plan."])[:3]


def _goals_to_delay(gap, dimensions: list[ReadinessDimension]) -> list[str]:
    delay = []
    if any(item.dimension_id == "combat" and item.score < 60 for item in dimensions):
        delay.append("High-pressure group content until a playable build is verified.")
    if gap.missing_requirements:
        delay.append("Expensive legendary spending until blockers and do-not-sell materials are reviewed.")
    return delay or ["No major delay recommendation from current evidence."]


def _safe_goals(dimensions: list[ReadinessDimension], progress_percent: float) -> list[str]:
    safe = ["Daily time-gated progress that advances the active goal manually."]
    if progress_percent >= 25:
        safe.append("Low-risk collection cleanup with known missing steps.")
    if any(item.dimension_id == "combat" and item.score < 60 for item in dimensions):
        safe.append("Open-world build recovery before optimized group content.")
    return safe


def _data_freshness(graph: GraphData) -> str:
    if not graph.evidence:
        return "No evidence loaded; run account sync or load demo graph."
    return "Evidence loaded; refresh account and market data before costly manual decisions."


def _report_assumptions(dimensions: list[ReadinessDimension]) -> list[str]:
    assumptions: list[str] = []
    for dimension in dimensions:
        assumptions.extend(dimension.assumptions)
    return sorted(set(assumptions))


def _status_for_score(score: int | float) -> str:
    if score >= 75:
        return "ready"
    if score >= 50:
        return "recoverable"
    return "needs_review"
