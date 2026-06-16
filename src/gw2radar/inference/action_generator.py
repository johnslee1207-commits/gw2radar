from gw2radar.graph.graph_query import GraphData
from gw2radar.inference.action_ranker import rank_action
from gw2radar.inference.goal_gap import calculate_goal_gap
from gw2radar.inference.material_policy import generate_material_policy_actions
from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import Action, Relation


def generate_actions(graph: GraphData, goal_id: str) -> list[Action]:
    gap = calculate_goal_gap(graph, goal_id)
    actions = generate_material_policy_actions(graph, goal_id)

    for missing in gap.missing_requirements:
        if missing.entity_id == "gw2:item:mystic_clover":
            actions.append(_missing_mystic_clover_action(graph, goal_id, missing.entity_id))
        elif missing.entity_id == "gw2:currency:unbound_magic":
            actions.extend(_unbound_magic_actions(graph, goal_id, missing.entity_id))
        elif missing.entity_type == EntityType.ACHIEVEMENT:
            actions.append(_achievement_action(graph, goal_id, missing.entity_id, missing.name))

    actions = sorted(_dedupe_actions(actions), key=lambda action: action.priority_score, reverse=True)
    graph.replace_actions_for_goal(goal_id, actions)
    _add_advances_goal_relations(graph, goal_id, actions)
    return actions


def _evidence_refs(graph: GraphData) -> list[str]:
    return list(graph.evidence.keys())


def _missing_mystic_clover_action(graph: GraphData, goal_id: str, entity_id: str) -> Action:
    return Action(
        id=f"action:watch_price:{goal_id}:{entity_id}",
        action_type=ActionType.WATCH_PRICE,
        title="Watch Mystic Clover acquisition options",
        description="Compare manual acquisition routes before spending account resources.",
        target_entity_id=entity_id,
        target_goal_id=goal_id,
        priority_score=rank_action(
            ActionType.WATCH_PRICE,
            advances_goal=True,
            resolves_missing_requirement=True,
        ),
        urgency="medium",
        preconditions=["player manually chooses an acquisition route"],
        expected_outputs=["Mystic Clover gap is reduced by manual acquisition"],
        costs={"currency_or_material_spend": "player_review_required"},
        constraints={"recommendation_only": True, "no_auto_buy": True, "no_auto_craft": True},
        reason_codes=["missing_requirement", "review_acquisition_options"],
        evidence_refs=_evidence_refs(graph),
        properties={"candidate_for": ["buy", "craft"]},
        explanation="Mystic Clover is below the Aurora requirement; review acquisition options before committing resources.",
    )


def _unbound_magic_actions(graph: GraphData, goal_id: str, entity_id: str) -> list[Action]:
    actions: list[Action] = []
    for relation in graph.relations:
        if relation.predicate != RelationType.PRODUCES or relation.object_id != entity_id:
            continue
        task = graph.entities[relation.subject_id]
        estimated_minutes = int(task.properties.get("estimated_minutes", 0))
        actions.append(
            Action(
                id=f"action:daily:{goal_id}:{task.id}",
                action_type=ActionType.DO_DAILY,
                title=f"Do {task.canonical_name}",
                description=f"Manual route estimated at {estimated_minutes} minutes.",
                target_entity_id=task.id,
                target_goal_id=goal_id,
                priority_score=rank_action(
                    ActionType.DO_DAILY,
                    advances_goal=True,
                    resolves_missing_requirement=True,
                    is_time_gated=True,
                    estimated_minutes=estimated_minutes,
                ),
                urgency="high",
                preconditions=["player manually completes the route in game"],
                expected_outputs=["Unbound Magic progress toward Aurora"],
                costs={"estimated_minutes": estimated_minutes},
                constraints={"recommendation_only": True, "no_gameplay_automation": True},
                reason_codes=["missing_requirement", "daily_task", "advances_active_goal"],
                evidence_refs=_evidence_refs(graph),
                properties={
                    "produces_entity_id": entity_id,
                    "estimated_quantity": relation.properties.get("estimated_quantity"),
                    "estimated_minutes": estimated_minutes,
                },
                explanation=(
                    f"{task.canonical_name} produces Unbound Magic and advances Aurora without automation."
                ),
            )
        )
    if not actions:
        actions.append(
            Action(
                id=f"action:farm:{goal_id}:{entity_id}",
                action_type=ActionType.FARM,
                title="Farm Unbound Magic",
                target_entity_id=entity_id,
                target_goal_id=goal_id,
                priority_score=rank_action(
                    ActionType.FARM,
                    advances_goal=True,
                    resolves_missing_requirement=True,
                ),
                urgency="medium",
                preconditions=["player manually farms in game"],
                expected_outputs=["Unbound Magic gap is reduced"],
                constraints={"recommendation_only": True, "no_gameplay_automation": True},
                reason_codes=["missing_requirement", "farm_candidate"],
                evidence_refs=_evidence_refs(graph),
                explanation="Unbound Magic is below the Aurora requirement; farm it through manual in-game activities.",
            )
        )
    return actions


def _achievement_action(graph: GraphData, goal_id: str, entity_id: str, name: str) -> Action:
    return Action(
        id=f"action:achievement:{goal_id}:{entity_id}",
        action_type=ActionType.COMPLETE_ACHIEVEMENT,
        title=f"Complete {name}",
        description="Finish the missing collection or achievement step manually in game.",
        target_entity_id=entity_id,
        target_goal_id=goal_id,
        priority_score=rank_action(
            ActionType.COMPLETE_ACHIEVEMENT,
            advances_goal=True,
            resolves_missing_requirement=True,
        ),
        urgency="medium",
        preconditions=["player manually completes the achievement in game"],
        expected_outputs=[f"{name} no longer blocks Aurora"],
        constraints={"recommendation_only": True, "no_gameplay_automation": True},
        reason_codes=["missing_requirement", "blocks_active_goal", "achievement_progress"],
        evidence_refs=_evidence_refs(graph),
        properties={"blocks_goal": True},
        explanation=f"{name} is missing and blocks Aurora progress.",
    )


def _dedupe_actions(actions: list[Action]) -> list[Action]:
    deduped: dict[str, Action] = {}
    for action in actions:
        deduped[action.id] = action
    return list(deduped.values())


def _add_advances_goal_relations(graph: GraphData, goal_id: str, actions: list[Action]) -> None:
    evidence_id = next(iter(graph.evidence.keys()), None)
    for action in actions:
        relation_id = f"rel:{action.id}:advances:{goal_id}"
        if any(relation.id == relation_id for relation in graph.relations):
            continue
        graph.add_relation(
            Relation(
                id=relation_id,
                subject_id=action.id,
                predicate=RelationType.ADVANCES_GOAL,
                object_id=goal_id,
                graph_layer=GraphLayer.PERSONAL_INTELLIGENCE,
                properties={"priority_score": action.priority_score},
                evidence_id=evidence_id,
            )
        )
