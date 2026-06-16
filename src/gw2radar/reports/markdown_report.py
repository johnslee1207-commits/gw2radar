from gw2radar.graph.graph_query import GraphData
from gw2radar.inference.action_generator import generate_actions
from gw2radar.inference.goal_gap import calculate_goal_gap
from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.schemas import Action, GoalGapItem


def generate_markdown_report(graph: GraphData, goal_id: str) -> str:
    gap = calculate_goal_gap(graph, goal_id)
    actions = graph.actions_for_goal(goal_id) or generate_actions(graph, goal_id)
    today = [a for a in actions if a.urgency == "today" or a.action_type == ActionType.DO_DAILY]
    week = [a for a in actions if a not in today]
    reserved = [
        a for a in actions if a.action_type in {ActionType.HOLD, ActionType.RESERVE_FOR_GOAL}
    ]

    lines = [
        "# GW2Radar MVP 0.1 Daily Goal Report",
        "",
        "## Account Summary",
        f"- Account: {graph.account_id or 'unknown'}",
        "",
        "## Active Goal",
        f"- {gap.goal_name}",
        "",
        "## Goal Progress",
        f"- Progress: {gap.progress_percent:.2f}%",
        "",
        "## Completed Requirements",
        *_format_gap_items(gap.completed_requirements),
        "",
        "## Missing Requirements",
        *_format_gap_items(gap.missing_requirements),
        "",
        "## Reserved / Do Not Sell Materials",
        *_format_actions(reserved),
        "",
        "## Recommended Actions Today",
        *_format_actions(today),
        "",
        "## Recommended Actions This Week",
        *_format_actions(week),
        "",
        "## Evidence Notes",
        "- Data source: mock fixtures for MVP 0.1.",
        "- Recommendations are informational only and require manual player action.",
    ]
    return "\n".join(lines) + "\n"


def _format_gap_items(items: list[GoalGapItem]) -> list[str]:
    if not items:
        return ["- None"]
    return [
        (
            f"- {item.name}: required {item.required_quantity:g}, "
            f"owned {item.owned_quantity:g}, missing {item.missing_quantity:g}"
        )
        for item in items
    ]


def _format_actions(actions: list[Action]) -> list[str]:
    if not actions:
        return ["- None"]
    return [
        (
            f"- {action.title} (priority {action.priority_score:.2f})\n"
            f"  - Reason: {action.explanation}"
        )
        for action in actions
    ]
