from gw2radar.graph.graph_query import GraphData
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import GoalGapItem, GoalGapResult, Relation


def calculate_goal_gap(graph: GraphData, goal_id: str) -> GoalGapResult:
    goal = graph.entities[goal_id]
    completed: list[GoalGapItem] = []
    missing: list[GoalGapItem] = []
    surplus: dict[str, float] = {}

    requirements = goal.properties.get("requirements", [])
    for req in requirements:
        entity_id = req["entity_id"]
        required_quantity = float(req["required_quantity"])
        owned_quantity = graph.quantity_owned(entity_id)
        missing_quantity = max(required_quantity - owned_quantity, 0.0)
        entity = graph.entities[entity_id]
        item = GoalGapItem(
            entity_id=entity_id,
            name=entity.canonical_name,
            entity_type=EntityType(req["type"]),
            required_quantity=required_quantity,
            owned_quantity=owned_quantity,
            missing_quantity=missing_quantity,
            completed=missing_quantity == 0,
        )
        if item.completed:
            completed.append(item)
            if owned_quantity > required_quantity:
                surplus[entity_id] = owned_quantity - required_quantity
        else:
            missing.append(item)
            _add_missing_relation(graph, goal_id, item)

    progress = (len(completed) / len(requirements) * 100) if requirements else 0.0
    return GoalGapResult(
        goal_id=goal_id,
        goal_name=goal.canonical_name,
        progress_percent=round(progress, 2),
        completed_requirements=completed,
        missing_requirements=missing,
        surplus_quantities=surplus,
    )


def _add_missing_relation(graph: GraphData, goal_id: str, item: GoalGapItem) -> None:
    relation_id = f"rel:{item.entity_id}:missing_for:{goal_id}"
    if any(relation.id == relation_id for relation in graph.relations):
        return
    graph.add_relation(
        Relation(
            id=relation_id,
            subject_id=item.entity_id,
            predicate=RelationType.MISSING_FOR_GOAL,
            object_id=goal_id,
            graph_layer=GraphLayer.PERSONAL_INTELLIGENCE,
            properties={"missing_quantity": item.missing_quantity},
            evidence_id=next(iter(graph.evidence.keys()), None),
        )
    )
