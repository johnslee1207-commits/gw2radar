from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from gw2radar.commercial.account_value import build_goal_reservation_index
from gw2radar.commercial.legendary_planner import (
    LegendaryPlannerResult,
    add_legendary_goal,
    recompute_legendary_plan,
)
from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import QAStatus, Relation


class ActionPreconditionError(Exception):
    pass


class ActionQAFailError(Exception):
    pass


@dataclass
class ActionEffect:
    description: str
    affected_entity_ids: list[str] = field(default_factory=list)
    relations_created: list[dict[str, str]] = field(default_factory=list)
    snapshots_invalidated: list[str] = field(default_factory=list)


@dataclass
class ActionRegistryEntry:
    action_type: str
    title: str
    description: str
    input_schema: dict[str, str]
    preconditions: list[str]
    effects: list[str]
    qa_hooks: list[str]
    privacy_policy: str = "private_summary_only"


REGISTRY: dict[str, ActionRegistryEntry] = {
    "reserve_material_for_goal": ActionRegistryEntry(
        action_type="reserve_material_for_goal",
        title="Reserve Material for Goal",
        description="Marks a quantity of a material as reserved for an active legendary goal.",
        input_schema={
            "account_id": "str",
            "item_id": "str",
            "goal_id": "str",
            "quantity": "float",
        },
        preconditions=[
            "account_snapshot_exists",
            "item_owned_by_account",
            "goal_active",
            "item_required_by_goal",
        ],
        effects=[
            "create_relation: reserved_for",
            "update_property: reserved_quantity",
            "update_property: safe_surplus_quantity",
        ],
        qa_hooks=[
            "reserved_quantity_not_exceed_owned",
            "goal_requirement_resolves",
        ],
    ),
    "generate_do_not_sell": ActionRegistryEntry(
        action_type="generate_do_not_sell",
        title="Generate Do-Not-Sell List",
        description="Computes materials that should not be sold because they are reserved for active goals.",
        input_schema={
            "goal_id": "str",
        },
        preconditions=[
            "goals_active",
            "account_snapshot_exists",
        ],
        effects=[
            "generate_do_not_sell_entities",
            "create_relation: reserved_for",
        ],
        qa_hooks=[
            "reserved_quantity_not_exceed_owned",
            "private_data_not_public",
        ],
    ),
    "generate_legendary_plan": ActionRegistryEntry(
        action_type="generate_legendary_plan",
        title="Generate Legendary Plan",
        description="Recomputes the full legendary planner for a goal.",
        input_schema={
            "goal_id": "str",
        },
        preconditions=[
            "goals_active",
            "account_snapshot_exists",
        ],
        effects=[
            "generate_missing_requirements",
            "update_do_not_sell",
            "generate_actions",
        ],
        qa_hooks=[
            "goal_requirement_resolves",
            "evidence_refs_exist",
        ],
    ),
}


def check_preconditions(
    entry: ActionRegistryEntry,
    graph: GraphData,
    session: Session | None = None,
    **kwargs: Any,
) -> list[str]:
    failures: list[str] = []
    for pc in entry.preconditions:
        if pc == "account_snapshot_exists":
            if not graph.account_id or graph.account_id not in graph.entities:
                failures.append("account_snapshot_exists: No account entity found in graph.")
        elif pc == "goal_active":
            goals = [e for e in graph.entities.values() if e.type.value == "goal"]
            if not goals:
                failures.append("goal_active: No goal entities found in graph.")
        elif pc == "goals_active":
            goals = [e for e in graph.entities.values() if e.type.value == "goal"]
            if not goals:
                failures.append("goals_active: No goal entities found in graph.")
        elif pc == "item_owned_by_account":
            item_id = kwargs.get("item_id", "")
            owned = graph.quantity_owned(item_id)
            if owned <= 0:
                failures.append(f"item_owned_by_account: {item_id} not owned (owned={owned}).")
        elif pc == "item_required_by_goal":
            item_id = kwargs.get("item_id", "")
            goal_id = kwargs.get("goal_id", "")
            reqs = graph.find_relations(predicate=RelationType.REQUIRES, object_id=item_id)
            goal_reqs = [r for r in reqs if r.subject_id == goal_id] if goal_id else reqs
            if not goal_reqs:
                failures.append(f"item_required_by_goal: {item_id} not required by {goal_id or 'any goal'}.")
    return failures


def run_qa_hooks(entry: ActionRegistryEntry, graph: GraphData) -> list[str]:
    failures: list[str] = []
    for hook in entry.qa_hooks:
        if hook == "reserved_quantity_not_exceed_owned":
            for rel in graph.find_relations(predicate=RelationType.RESERVED_FOR_GOAL):
                qty = rel.properties.get("reserved_quantity", 0)
                owned = graph.quantity_owned(rel.subject_id)
                if isinstance(qty, (int, float)) and qty > owned:
                    failures.append(f"reserved_quantity_not_exceed_owned: {rel.subject_id} reserved {qty} > owned {owned}")
        elif hook == "private_data_not_public":
            for eid, entity in graph.entities.items():
                for ref in entity.source_refs:
                    if ref.privacy_scope == "private_summary_only":
                        pass
        elif hook == "evidence_refs_exist":
            if not graph.evidence:
                failures.append("evidence_refs_exist: No evidence in graph.")
        elif hook == "goal_requirement_resolves":
            for entity in graph.entities.values():
                if entity.type.value == "goal":
                    reqs = graph.find_relations(subject_id=entity.id, predicate=RelationType.REQUIRES)
                    if not reqs:
                        failures.append(f"goal_requirement_resolves: {entity.id} has no REQUIRES relations.")
    return failures


def reserve_material_for_goal(
    graph: GraphData,
    session: Session,
    *,
    item_id: str,
    goal_id: str,
    quantity: float,
) -> ActionEffect:
    entry = REGISTRY["reserve_material_for_goal"]
    failures = check_preconditions(entry, graph, session, item_id=item_id, goal_id=goal_id)
    if failures:
        raise ActionPreconditionError(f"Precondition failures: {'; '.join(failures)}")

    owned = graph.quantity_owned(item_id)
    if quantity > owned:
        raise ActionPreconditionError(f"Cannot reserve {quantity} of {item_id}: only {owned} owned.")

    existing = graph.find_relations(
        subject_id=item_id,
        predicate=RelationType.RESERVED_FOR_GOAL,
        object_id=goal_id,
    )
    if existing:
        existing[0].properties["reserved_quantity"] = quantity
    else:
        graph.add_relation(
            Relation(
                id=f"rel:reserved:{item_id}:{goal_id}",
                subject_id=item_id,
                predicate=RelationType.RESERVED_FOR_GOAL,
                object_id=goal_id,
                graph_layer=GraphLayer.PERSONAL_INTELLIGENCE,
                properties={"reserved_quantity": quantity},
            )
        )

    effect = ActionEffect(
        description=f"Reserved {quantity} of {item_id} for {goal_id}",
        affected_entity_ids=[item_id, goal_id],
        relations_created=[{"type": "reserved_for", "subject": item_id, "object": goal_id}],
    )

    qa_fails = run_qa_hooks(entry, graph)
    if qa_fails:
        raise ActionQAFailError(f"QA failures: {'; '.join(qa_fails)}")

    return effect


def generate_do_not_sell(graph: GraphData, session: Session, goal_id: str) -> ActionEffect:
    entry = REGISTRY["generate_do_not_sell"]
    failures = check_preconditions(entry, graph, session)
    if failures:
        raise ActionPreconditionError(f"Precondition failures: {'; '.join(failures)}")

    owner = graph.account_id
    for ps in graph.player_state:
        if ps.location not in {"materials", "currencies"}:
            continue
        reservation = build_goal_reservation_index(session, graph)
        entity_res = reservation.get(ps.entity_id, {})
        reserved_qty = float(entity_res.get("reserved_quantity", 0.0) or 0.0)
        if reserved_qty <= 0:
            continue
        existing = graph.find_relations(
            subject_id=ps.entity_id,
            predicate=RelationType.RESERVED_FOR_GOAL,
        )
        if not existing:
            graph.add_relation(
                Relation(
                    id=f"rel:dns:{ps.entity_id}:{goal_id}",
                    subject_id=ps.entity_id,
                    predicate=RelationType.RESERVED_FOR_GOAL,
                    object_id=goal_id,
                    graph_layer=GraphLayer.PERSONAL_INTELLIGENCE,
                    properties={"reserved_quantity": reserved_qty, "source": "do_not_sell"},
                )
            )

    qa_fails = run_qa_hooks(entry, graph)
    if qa_fails:
        raise ActionQAFailError(f"QA failures: {'; '.join(qa_fails)}")

    return ActionEffect(
        description=f"Generated do-not-sell list for {goal_id}",
        affected_entity_ids=[goal_id],
    )


def generate_legendary_plan(graph: GraphData, session: Session, goal_id: str) -> ActionEffect:
    entry = REGISTRY["generate_legendary_plan"]
    failures = check_preconditions(entry, graph, session)
    if failures:
        raise ActionPreconditionError(f"Precondition failures: {'; '.join(failures)}")

    goals_already = bool(graph.find_relations(subject_id=goal_id, predicate=RelationType.REQUIRES))
    if not goals_already:
        add_legendary_goal(session, graph, goal_id)
    recompute_legendary_plan(session, graph)

    qa_fails = run_qa_hooks(entry, graph)
    if qa_fails:
        raise ActionQAFailError(f"QA failures: {'; '.join(qa_fails)}")

    return ActionEffect(
        description=f"Generated legendary plan for {goal_id}",
        affected_entity_ids=[goal_id],
    )


def list_registry() -> dict[str, ActionRegistryEntry]:
    return dict(REGISTRY)
