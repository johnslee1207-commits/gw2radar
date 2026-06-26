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
    nodes = _schedule_nodes(candidates)
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


def _action_type_priority(at: str) -> int:
    order = {
        "do_daily": 0,
        "do_weekly": 0,
        "watch_price": 1,
        "reserve_for_goal": 1,
        "farm": 2,
        "buy": 3,
        "exchange": 3,
        "craft": 4,
        "sell_surplus": 4,
        "hold": 5,
        "complete_achievement": 5,
        "complete_collection_step": 5,
        "generate_daily_plan": 6,
        "generate_weekly_plan": 6,
    }
    return order.get(at, 5)


def _action_type_group(at: str) -> str:
    if at in {"do_daily", "do_weekly"}:
        return "routine"
    if at in {"watch_price", "buy", "sell_surplus", "exchange"}:
        return "market"
    if at in {"farm", "craft"}:
        return "gather_craft"
    if at in {"reserve_for_goal", "hold"}:
        return "portfolio"
    if at in {"complete_achievement", "complete_collection_step"}:
        return "achievement"
    return "other"


def _schedule_nodes(candidates: list[ProgressionDecisionCandidate]) -> list[SevenDayPlanNode]:
    nodes: list[SevenDayPlanNode] = []
    group_budget: dict[str, int] = {}
    for index, candidate in enumerate(candidates, start=1):
        node = _node_for_candidate(candidate, index)
        nodes.append(node)
        group = _action_type_group(candidate.action_type)
        group_budget[group] = group_budget.get(group, 0) + node.estimated_minutes

    nodes.sort(key=lambda n: (_action_type_priority(n.action_type), -n.final_score, n.title))

    day_load: list[int] = [0] * 8
    day_group_count: dict[int, set[str]] = {d: set() for d in range(1, 8)}

    for node in nodes:
        placed = False
        for day in range(1, 8):
            group = _action_type_group(node.action_type)
            if day_load[day] + node.estimated_minutes <= 120 and group not in day_group_count[day]:
                node.day = day
                day_load[day] += node.estimated_minutes
                day_group_count[day].add(group)
                placed = True
                break
        if not placed:
            for day in range(1, 8):
                if day_load[day] + node.estimated_minutes <= 120:
                    node.day = day
                    day_load[day] += node.estimated_minutes
                    placed = True
                    break
        if not placed:
            lightest = min(range(1, 8), key=lambda d: day_load[d])
            node.day = lightest
            day_load[lightest] += node.estimated_minutes

    nodes.sort(key=lambda n: (n.day, _action_type_priority(n.action_type), -n.final_score))
    return nodes


def _node_for_candidate(candidate: ProgressionDecisionCandidate, rank: int) -> SevenDayPlanNode:
    return SevenDayPlanNode(
        node_id=f"plan-node-{rank}",
        day=1,
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
    edge_id = 0

    node_by_id = {n.node_id: n for n in nodes}
    for node in nodes:
        deps = _dependency_targets(node, node_by_id)
        for dep in deps:
            edge_id += 1
            edges.append(
                SevenDayPlanEdge(
                    edge_id=f"plan-edge-{edge_id}",
                    source_node_id=dep.node_id,
                    target_node_id=node.node_id,
                    relation="blocks",
                    rationale=dep.rationale,
                )
            )

    if not edges and len(nodes) > 1:
        for i in range(1, len(nodes)):
            edge_id += 1
            edges.append(
                SevenDayPlanEdge(
                    edge_id=f"plan-edge-{edge_id}",
                    source_node_id=nodes[i - 1].node_id,
                    target_node_id=nodes[i].node_id,
                    relation="review_before_next_step",
                    rationale="Review the previous manual step and update local facts before relying on the next candidate.",
                )
            )
    return edges


def _dependency_targets(node: SevenDayPlanNode, all_nodes: dict[str, SevenDayPlanNode]) -> list[SevenDayPlanEdge]:
    deps: list[SevenDayPlanEdge] = []
    at = node.action_type
    same_item = [n for n in all_nodes.values() if n.action_id != node.action_id and n.node_id != node.node_id]

    if at == "buy":
        watchers = [n for n in same_item if n.action_type == "watch_price"]
        for w in watchers:
            deps.append(SevenDayPlanEdge(edge_id="", source_node_id=w.node_id, target_node_id=node.node_id, relation="blocks", rationale="Observe price before committing to a purchase."))

    if at == "craft":
        gatherers = [n for n in same_item if n.action_type in {"farm", "buy"}]
        for g in gatherers:
            deps.append(SevenDayPlanEdge(edge_id="", source_node_id=g.node_id, target_node_id=node.node_id, relation="blocks", rationale="Gather or buy materials before crafting."))

    if at == "sell_surplus":
        watchers = [n for n in same_item if n.action_type == "watch_price"]
        for w in watchers:
            deps.append(SevenDayPlanEdge(edge_id="", source_node_id=w.node_id, target_node_id=node.node_id, relation="blocks", rationale="Review price trend before listing surplus."))

    return deps


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
