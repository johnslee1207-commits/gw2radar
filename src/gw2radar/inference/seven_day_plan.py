import csv
import io

from pydantic import BaseModel, Field

from gw2radar.inference.progression_decision_engine import (
    ProgressionDecisionCandidate,
    ProgressionDecisionResult,
)


class SevenDayPlanNode(BaseModel):
    node_id: str
    day: int
    action_id: str
    title: str
    action_type: str
    estimated_minutes: int
    final_score: float
    recommendation_strength: str
    status: str = "review_candidate"
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    manual_action_boundary: str = "Plan step is informational only and requires manual player review."


class SevenDayPlanEdge(BaseModel):
    edge_id: str
    source_node_id: str
    target_node_id: str
    relation: str
    rationale: str


class SevenDayPlanDay(BaseModel):
    day: int
    label: str
    estimated_minutes: int
    nodes: list[SevenDayPlanNode]


class SevenDayPlan(BaseModel):
    schema_version: str = "gw2radar.seven_day_plan.v1"
    goal_id: str
    plan_horizon_days: int = 7
    node_count: int
    edge_count: int
    total_estimated_minutes: int
    days: list[SevenDayPlanDay]
    nodes: list[SevenDayPlanNode]
    edges: list[SevenDayPlanEdge]
    assumptions: list[str]
    safety_boundaries: list[str]
    deferred_capabilities: list[str]


def build_seven_day_plan(decision_result: ProgressionDecisionResult) -> SevenDayPlan:
    candidates = decision_result.candidates
    nodes = [_node_for_candidate(candidate) for candidate in candidates]
    edges = _dependency_edges(nodes)
    days = [
        SevenDayPlanDay(
            day=day,
            label=f"Day {day}",
            estimated_minutes=sum(node.estimated_minutes for node in nodes if node.day == day),
            nodes=[node for node in nodes if node.day == day],
        )
        for day in range(1, 8)
    ]
    return SevenDayPlan(
        goal_id=decision_result.goal_id,
        node_count=len(nodes),
        edge_count=len(edges),
        total_estimated_minutes=sum(node.estimated_minutes for node in nodes),
        days=days,
        nodes=nodes,
        edges=edges,
        assumptions=[
            "Plan is generated from the current local graph snapshot and reviewed decision candidates.",
            "Missing or low-confidence facts remain warnings or assumptions.",
            "The player decides whether and when to perform every step.",
        ],
        safety_boundaries=[
            "The plan never executes gameplay, trading, crafting, gear changes, or market actions.",
            "The DAG expresses planning dependencies only; it is not an automation workflow.",
            "No completion date, market return, or profit outcome is guaranteed.",
        ],
        deferred_capabilities=[
            "real-time autonomous replanning",
            "automatic gameplay execution",
            "automatic trading",
            "guaranteed completion",
        ],
    )


def render_seven_day_plan_markdown(plan: SevenDayPlan) -> str:
    lines = [
        "# GW2Radar 7-Day Planning DAG",
        "",
        f"- Goal: {plan.goal_id}",
        f"- Nodes: {plan.node_count}",
        f"- Edges: {plan.edge_count}",
        f"- Estimated minutes: {plan.total_estimated_minutes}",
        "",
        "## Daily Plan",
    ]
    for day in plan.days:
        lines.extend(["", f"### {day.label}", f"- Estimated minutes: {day.estimated_minutes}"])
        if not day.nodes:
            lines.append("- Review day / no generated step.")
        for node in day.nodes:
            lines.append(f"- {node.title} ({node.action_type}, score {node.final_score:.2f})")
            lines.append(f"  - Boundary: {node.manual_action_boundary}")
            if node.warnings:
                lines.append(f"  - Warnings: {'; '.join(node.warnings)}")
    lines.extend(["", "## Dependencies"])
    if not plan.edges:
        lines.append("- None.")
    for edge in plan.edges:
        lines.append(f"- {edge.source_node_id} -> {edge.target_node_id}: {edge.rationale}")
    lines.extend(["", "## Assumptions"])
    lines.extend(f"- {item}" for item in plan.assumptions)
    lines.extend(["", "## Safety Boundaries"])
    lines.extend(f"- {item}" for item in plan.safety_boundaries)
    return "\n".join(lines) + "\n"


def render_seven_day_plan_csv(plan: SevenDayPlan) -> str:
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(
        [
            "row_type",
            "day",
            "node_id",
            "action_id",
            "title",
            "action_type",
            "estimated_minutes",
            "final_score",
            "status",
            "warnings",
        ]
    )
    for node in plan.nodes:
        writer.writerow(
            [
                "node",
                node.day,
                node.node_id,
                node.action_id,
                node.title,
                node.action_type,
                node.estimated_minutes,
                f"{node.final_score:.4f}",
                node.status,
                "; ".join(node.warnings),
            ]
        )
    for edge in plan.edges:
        writer.writerow(
            [
                "edge",
                "",
                edge.source_node_id,
                edge.target_node_id,
                edge.relation,
                edge.rationale,
                "",
                "",
                "",
                "",
            ]
        )
    return output.getvalue()


def _node_for_candidate(candidate: ProgressionDecisionCandidate) -> SevenDayPlanNode:
    day = ((candidate.rank - 1) % 7) + 1
    return SevenDayPlanNode(
        node_id=f"plan-node-{candidate.rank}",
        day=day,
        action_id=candidate.action_id,
        title=candidate.title,
        action_type=candidate.action_type,
        estimated_minutes=_estimated_minutes(candidate),
        final_score=candidate.final_score,
        recommendation_strength=candidate.recommendation_strength,
        assumptions=candidate.assumptions,
        warnings=candidate.warnings,
        evidence_refs=candidate.evidence_refs,
    )


def _dependency_edges(nodes: list[SevenDayPlanNode]) -> list[SevenDayPlanEdge]:
    edges: list[SevenDayPlanEdge] = []
    for index, node in enumerate(nodes[1:], start=1):
        previous = nodes[index - 1]
        edges.append(
            SevenDayPlanEdge(
                edge_id=f"plan-edge-{index}",
                source_node_id=previous.node_id,
                target_node_id=node.node_id,
                relation="review_before_next_step",
                rationale="Review the previous manual step and update local facts before relying on the next candidate.",
            )
        )
    return edges


def _estimated_minutes(candidate: ProgressionDecisionCandidate) -> int:
    costs = candidate.action.get("costs") or {}
    if isinstance(costs.get("estimated_minutes"), int):
        return max(5, min(int(costs["estimated_minutes"]), 180))
    if candidate.action_type in {"do_daily", "do_weekly"}:
        return 20
    if candidate.action_type in {"reserve_for_goal", "hold"}:
        return 10
    if candidate.action_type in {"watch_price", "buy", "sell_surplus"}:
        return 15
    if candidate.action_type in {"complete_achievement", "complete_collection_step"}:
        return 45
    return 30
