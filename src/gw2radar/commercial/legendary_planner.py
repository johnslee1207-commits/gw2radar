from collections import defaultdict
from datetime import datetime
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.db.models import GoalPortfolioModel, LegendaryGoalModel, utc_now
from gw2radar.graph.graph_query import GraphData
from gw2radar.inference.goal_gap import calculate_goal_gap
from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.entity_types import EntityType


DEFAULT_USER_ID = "local-user"
DEFAULT_PORTFOLIO_ID = "portfolio_local_user_default"


class LegendaryPathType(StrEnum):
    CHEAP = "cheap"
    FAST = "fast"


class LegendaryGoalInput(BaseModel):
    graph_goal_id: str = "gw2:goal:aurora"
    priority: int = 100


class LegendaryGoalRecord(BaseModel):
    goal_record_id: str
    portfolio_id: str
    user_id: str
    graph_goal_id: str
    display_name: str
    priority: int
    active: bool
    created_at: datetime
    updated_at: datetime


class GoalPortfolio(BaseModel):
    portfolio_id: str
    user_id: str
    name: str
    goals: list[LegendaryGoalRecord] = Field(default_factory=list)


class SharedRequirement(BaseModel):
    entity_id: str
    name: str
    required_by_goal_ids: list[str]
    total_required_quantity: float
    owned_quantity: float
    missing_quantity: float


class GoalConflict(BaseModel):
    entity_id: str
    name: str
    conflict_type: str
    explanation: str


class TimeGate(BaseModel):
    entity_id: str
    name: str
    gate_type: str
    explanation: str


class AcquisitionMethod(BaseModel):
    entity_id: str
    name: str
    method: str
    estimated_quantity: float | None = None
    repeatability: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class LegendaryPathStep(BaseModel):
    entity_id: str
    name: str
    missing_quantity: float
    path_type: LegendaryPathType
    rationale: str


class MaterialReservation(BaseModel):
    entity_id: str
    name: str
    owned_quantity: float
    reserved_for_goal_ids: list[str]
    policy: str
    explanation: str


class LegendaryPlannerResult(BaseModel):
    portfolio: GoalPortfolio
    shared_requirements: list[SharedRequirement]
    conflicts: list[GoalConflict]
    time_gates: list[TimeGate]
    acquisition_methods: list[AcquisitionMethod]
    cheap_path: list[LegendaryPathStep]
    fast_path: list[LegendaryPathStep]
    daily_route: list[str]
    weekly_route: list[str]
    do_not_sell: list[MaterialReservation]
    evidence_refs: list[str]


def ensure_default_portfolio(session: Session, graph: GraphData, user_id: str = DEFAULT_USER_ID) -> GoalPortfolio:
    portfolio = session.get(GoalPortfolioModel, DEFAULT_PORTFOLIO_ID)
    if portfolio is None:
        portfolio = GoalPortfolioModel(
            portfolio_id=DEFAULT_PORTFOLIO_ID,
            user_id=user_id,
            name="Default Legendary Portfolio",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(portfolio)
        session.commit()

    if not _active_goal_rows(session, portfolio.portfolio_id):
        first_goal = next((goal for goal in graph.goals() if goal.properties.get("goal_type") == "legendary"), None)
        if first_goal is not None:
            add_legendary_goal(session, graph, first_goal.id, user_id=user_id, priority=100)
    return get_portfolio(session, user_id)


def add_legendary_goal(
    session: Session,
    graph: GraphData,
    graph_goal_id: str,
    user_id: str = DEFAULT_USER_ID,
    priority: int = 100,
) -> LegendaryGoalRecord:
    if graph_goal_id not in graph.entities:
        raise ValueError("Goal not found.")
    portfolio = session.get(GoalPortfolioModel, DEFAULT_PORTFOLIO_ID)
    if portfolio is None:
        portfolio = GoalPortfolioModel(
            portfolio_id=DEFAULT_PORTFOLIO_ID,
            user_id=user_id,
            name="Default Legendary Portfolio",
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        session.add(portfolio)
        session.flush()

    existing = (
        session.query(LegendaryGoalModel)
        .filter(
            LegendaryGoalModel.portfolio_id == portfolio.portfolio_id,
            LegendaryGoalModel.graph_goal_id == graph_goal_id,
            LegendaryGoalModel.active.is_(True),
        )
        .first()
    )
    if existing is not None:
        existing.priority = priority
        existing.updated_at = utc_now()
        session.commit()
        return _goal_from_model(existing)

    graph_goal = graph.entities[graph_goal_id]
    goal = LegendaryGoalModel(
        goal_record_id=f"legendary_goal_{uuid4().hex}",
        portfolio_id=portfolio.portfolio_id,
        user_id=user_id,
        graph_goal_id=graph_goal_id,
        display_name=graph_goal.canonical_name,
        priority=priority,
        active=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    session.add(goal)
    session.commit()
    return _goal_from_model(goal)


def get_portfolio(session: Session, user_id: str = DEFAULT_USER_ID) -> GoalPortfolio:
    portfolio = (
        session.query(GoalPortfolioModel)
        .filter(GoalPortfolioModel.user_id == user_id)
        .order_by(GoalPortfolioModel.created_at)
        .first()
    )
    if portfolio is None:
        return GoalPortfolio(
            portfolio_id=DEFAULT_PORTFOLIO_ID,
            user_id=user_id,
            name="Default Legendary Portfolio",
            goals=[],
        )
    goals = [_goal_from_model(row) for row in _active_goal_rows(session, portfolio.portfolio_id)]
    return GoalPortfolio(
        portfolio_id=portfolio.portfolio_id,
        user_id=portfolio.user_id,
        name=portfolio.name,
        goals=goals,
    )


def recompute_legendary_plan(session: Session, graph: GraphData, user_id: str = DEFAULT_USER_ID) -> LegendaryPlannerResult:
    portfolio = ensure_default_portfolio(session, graph, user_id=user_id)
    goals = sorted(portfolio.goals, key=lambda goal: goal.priority)
    requirement_index: dict[str, dict] = {}
    goal_refs_by_requirement: dict[str, list[str]] = defaultdict(list)

    for goal in goals:
        gap = calculate_goal_gap(graph, goal.graph_goal_id)
        for item in gap.completed_requirements + gap.missing_requirements:
            entry = requirement_index.setdefault(
                item.entity_id,
                {
                    "name": item.name,
                    "entity_type": item.entity_type,
                    "total_required": 0.0,
                    "owned": item.owned_quantity,
                    "missing": 0.0,
                },
            )
            entry["total_required"] += item.required_quantity
            entry["owned"] = graph.quantity_owned(item.entity_id)
            goal_refs_by_requirement[item.entity_id].append(goal.graph_goal_id)

    for entity_id, entry in requirement_index.items():
        entry["missing"] = max(entry["total_required"] - entry["owned"], 0.0)

    shared = [
        SharedRequirement(
            entity_id=entity_id,
            name=entry["name"],
            required_by_goal_ids=goal_refs_by_requirement[entity_id],
            total_required_quantity=entry["total_required"],
            owned_quantity=entry["owned"],
            missing_quantity=entry["missing"],
        )
        for entity_id, entry in requirement_index.items()
        if len(set(goal_refs_by_requirement[entity_id])) > 1
    ]
    conflicts = [
        GoalConflict(
            entity_id=item.entity_id,
            name=item.name,
            conflict_type="shared_shortfall",
            explanation=f"{item.name} is shared by multiple goals and is short by {item.missing_quantity:g}.",
        )
        for item in shared
        if item.missing_quantity > 0
    ]
    time_gates = _infer_time_gates(graph, requirement_index)
    acquisitions = _infer_acquisition_methods(graph, requirement_index)
    missing_entries = [
        (entity_id, entry) for entity_id, entry in requirement_index.items() if entry["missing"] > 0
    ]
    cheap_path = _build_path(missing_entries, LegendaryPathType.CHEAP)
    fast_path = _build_path(missing_entries, LegendaryPathType.FAST)
    do_not_sell = _build_reservations(graph, requirement_index, goal_refs_by_requirement)
    return LegendaryPlannerResult(
        portfolio=portfolio,
        shared_requirements=sorted(shared, key=lambda item: item.name),
        conflicts=sorted(conflicts, key=lambda item: item.name),
        time_gates=sorted(time_gates, key=lambda item: item.name),
        acquisition_methods=sorted(acquisitions, key=lambda item: item.name),
        cheap_path=cheap_path,
        fast_path=fast_path,
        daily_route=_build_route(graph, "daily"),
        weekly_route=_build_route(graph, "weekly"),
        do_not_sell=sorted(do_not_sell, key=lambda item: item.name),
        evidence_refs=list(graph.evidence.keys()),
    )


def render_legendary_planner_report(result: LegendaryPlannerResult) -> str:
    lines = [
        "# Legendary Planner Pro Report",
        "",
        "## Active Legendary Portfolio",
        *[f"- {goal.display_name} (priority {goal.priority})" for goal in result.portfolio.goals],
        "",
        "## Recommended Goal Priority",
        *[f"- {goal.display_name}" for goal in sorted(result.portfolio.goals, key=lambda goal: goal.priority)],
        "",
        "## Shared Material Conflicts",
        *(_format_named(result.conflicts) or ["- None"]),
        "",
        "## Time-Gated Requirements",
        *(_format_named(result.time_gates) or ["- None"]),
        "",
        "## Daily Route",
        *[f"- {step}" for step in result.daily_route],
        "",
        "## Weekly Route",
        *[f"- {step}" for step in result.weekly_route],
        "",
        "## Cheapest Path",
        *[f"- {step.name}: {step.rationale}" for step in result.cheap_path],
        "",
        "## Fastest Path",
        *[f"- {step.name}: {step.rationale}" for step in result.fast_path],
        "",
        "## Do-Not-Sell List",
        *[f"- {item.name}: {item.explanation}" for item in result.do_not_sell],
        "",
        "## Evidence Notes",
        f"- Evidence refs: {', '.join(result.evidence_refs) if result.evidence_refs else 'none'}",
        "- Recommendations are informational only and require manual player action.",
        "- No gameplay automation, no automated trading, and no guaranteed-profit language.",
    ]
    return "\n".join(lines) + "\n"


def _infer_time_gates(graph: GraphData, requirement_index: dict[str, dict]) -> list[TimeGate]:
    gates: list[TimeGate] = []
    for entity_id, entry in requirement_index.items():
        entity = graph.entities[entity_id]
        if entry["entity_type"] in {EntityType.CURRENCY, EntityType.ACHIEVEMENT}:
            gates.append(
                TimeGate(
                    entity_id=entity_id,
                    name=entry["name"],
                    gate_type="account_progress",
                    explanation=f"{entry['name']} depends on account progress or repeatable play, not instant purchase.",
                )
            )
        elif entity.properties.get("legendary_related", False) and not entity.properties.get("tradable", False):
            gates.append(
                TimeGate(
                    entity_id=entity_id,
                    name=entry["name"],
                    gate_type="legendary_collection",
                    explanation=f"{entry['name']} is legendary-related and should be planned as a gated requirement.",
                )
            )
    return gates


def _infer_acquisition_methods(graph: GraphData, requirement_index: dict[str, dict]) -> list[AcquisitionMethod]:
    methods: list[AcquisitionMethod] = []
    for task in graph.entities.values():
        if task.type.value != "task":
            continue
        for produced in task.properties.get("produces", []):
            entity_id = produced.get("entity_id")
            if entity_id in requirement_index:
                methods.append(
                    AcquisitionMethod(
                        entity_id=entity_id,
                        name=graph.entity_name(entity_id),
                        method=task.canonical_name,
                        estimated_quantity=float(produced.get("estimated_quantity", 0)),
                        repeatability=task.properties.get("repeatability"),
                        evidence_refs=list(graph.evidence.keys()),
                    )
                )
    return methods


def _build_path(entries: list[tuple[str, dict]], path_type: LegendaryPathType) -> list[LegendaryPathStep]:
    if path_type == LegendaryPathType.CHEAP:
        ordered = sorted(entries, key=lambda pair: (pair[1]["entity_type"].value == "item", pair[1]["missing"]))
    else:
        ordered = sorted(entries, key=lambda pair: pair[1]["missing"], reverse=True)
    return [
        LegendaryPathStep(
            entity_id=entity_id,
            name=entry["name"],
            missing_quantity=entry["missing"],
            path_type=path_type,
            rationale=(
                f"Address {entry['missing']:g} missing via lower-risk manual acquisition first."
                if path_type == LegendaryPathType.CHEAP
                else f"Prioritize {entry['missing']:g} missing because it is the largest blocker."
            ),
        )
        for entity_id, entry in ordered[:5]
    ]


def _build_route(graph: GraphData, repeatability: str) -> list[str]:
    route = [
        task.canonical_name
        for task in graph.entities.values()
        if task.type.value == "task" and task.properties.get("repeatability") == repeatability
    ]
    return route or [f"No {repeatability} route available from current evidence."]


def _build_reservations(
    graph: GraphData,
    requirement_index: dict[str, dict],
    goal_refs_by_requirement: dict[str, list[str]],
) -> list[MaterialReservation]:
    reservations: list[MaterialReservation] = []
    for entity_id, entry in requirement_index.items():
        owned = graph.quantity_owned(entity_id)
        if owned <= 0:
            continue
        reservations.append(
            MaterialReservation(
                entity_id=entity_id,
                name=entry["name"],
                owned_quantity=owned,
                reserved_for_goal_ids=goal_refs_by_requirement[entity_id],
                policy="do_not_sell",
                explanation=f"Reserve {owned:g} {entry['name']} because it supports active legendary goals.",
            )
        )
    return reservations


def _active_goal_rows(session: Session, portfolio_id: str) -> list[LegendaryGoalModel]:
    return (
        session.query(LegendaryGoalModel)
        .filter(LegendaryGoalModel.portfolio_id == portfolio_id, LegendaryGoalModel.active.is_(True))
        .order_by(LegendaryGoalModel.priority, LegendaryGoalModel.created_at)
        .all()
    )


def _goal_from_model(row: LegendaryGoalModel) -> LegendaryGoalRecord:
    return LegendaryGoalRecord(
        goal_record_id=row.goal_record_id,
        portfolio_id=row.portfolio_id,
        user_id=row.user_id,
        graph_goal_id=row.graph_goal_id,
        display_name=row.display_name,
        priority=row.priority,
        active=row.active,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _format_named(items: list[GoalConflict] | list[TimeGate]) -> list[str]:
    return [f"- {item.name}: {item.explanation}" for item in items]
