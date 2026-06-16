from gw2radar.graph.graph_query import GraphData
from gw2radar.inference.action_generator import generate_actions
from gw2radar.inference.evidence_quality import evaluate_evidence_quality
from gw2radar.inference.goal_gap import calculate_goal_gap
from gw2radar.kb.kb_explanation import explain_actions_with_kb, render_kb_explanation_section
from gw2radar.kb.kb_models import KnowledgeRule
from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.schemas import Action, GoalGapItem


def generate_markdown_report(graph: GraphData, goal_id: str) -> str:
    gap = calculate_goal_gap(graph, goal_id)
    actions = graph.actions_for_goal(goal_id) or generate_actions(graph, goal_id)
    today = [a for a in actions if a.urgency == "high" or a.action_type == ActionType.DO_DAILY]
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
        *_format_evidence_notes(graph),
        "- Recommendations are informational only and require manual player action.",
    ]
    return "\n".join(lines) + "\n"


def generate_kb_backed_markdown_report(graph: GraphData, goal_id: str, rules: list[KnowledgeRule]) -> str:
    base_report = generate_markdown_report(graph, goal_id).rstrip()
    actions = graph.actions_for_goal(goal_id) or generate_actions(graph, goal_id)
    explanations = explain_actions_with_kb(actions, rules)
    lines = [
        base_report,
        "",
        *render_kb_explanation_section(explanations),
        "",
        "## Knowledge Base Boundary",
        "- KB explanations are applied only from reviewed and enabled rules.",
        "- KB explanations do not automate gameplay and do not replace manual player decisions.",
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
            f"  - Reason: {action.explanation}\n"
            f"  - Evidence quality: {action.properties.get('evidence_quality', {}).get('confidence_label', 'unknown')}"
        )
        for action in actions
    ]


def _format_evidence_notes(graph: GraphData) -> list[str]:
    evidence_refs = list(graph.evidence.keys())
    summary = evaluate_evidence_quality(graph, evidence_refs)
    notes = [
        f"- Evidence confidence: {summary.confidence_label}",
        f"- Minimum confidence: {summary.min_confidence:.2f}",
        f"- Stale evidence present: {str(summary.has_stale).lower()}",
    ]
    if graph.evidence:
        for evidence in graph.evidence.values():
            notes.append(
                f"- Source {evidence.id}: type={evidence.source_type}, confidence={evidence.confidence:.2f}"
            )
    else:
        notes.append("- No evidence records available; recommendations should be treated as low confidence.")
    return notes
