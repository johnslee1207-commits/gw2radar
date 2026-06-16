from gw2radar.graph.graph_query import GraphData
from gw2radar.inference.action_ranker import rank_action
from gw2radar.inference.goal_gap import calculate_goal_gap
from gw2radar.ontology.action_types import ActionType
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.schemas import Action


def generate_material_policy_actions(graph: GraphData, goal_id: str) -> list[Action]:
    gap = calculate_goal_gap(graph, goal_id)
    goal_name = gap.goal_name
    actions: list[Action] = []

    required_entity_ids = {
        item.entity_id for item in gap.completed_requirements + gap.missing_requirements
    }
    for entity_id in required_entity_ids:
        entity = graph.entities[entity_id]
        if entity.type not in {EntityType.ITEM, EntityType.MATERIAL, EntityType.CURRENCY}:
            continue
        owned_quantity = graph.quantity_owned(entity_id)
        if owned_quantity <= 0:
            continue
        actions.append(
            Action(
                id=f"action:reserve:{goal_id}:{entity_id}",
                action_type=ActionType.RESERVE_FOR_GOAL,
                title=f"Reserve {entity.canonical_name}",
                description=f"Keep {entity.canonical_name} allocated to {goal_name}.",
                target_entity_id=entity_id,
                target_goal_id=goal_id,
                priority_score=rank_action(
                    ActionType.RESERVE_FOR_GOAL,
                    advances_goal=True,
                    protects_required_material=True,
                ),
                urgency="normal",
                properties={"owned_quantity": owned_quantity},
                explanation=(
                    f"{entity.canonical_name} is required by {goal_name}; reserve it and do not sell it."
                ),
            )
        )

    if "gw2:item:mystic_coin" in required_entity_ids and graph.quantity_owned("gw2:item:mystic_coin") > 0:
        actions.append(
            Action(
                id=f"action:hold:{goal_id}:gw2:item:mystic_coin",
                action_type=ActionType.HOLD,
                title="Hold Mystic Coin",
                description="Keep Mystic Coins for Aurora.",
                target_entity_id="gw2:item:mystic_coin",
                target_goal_id=goal_id,
                priority_score=rank_action(
                    ActionType.HOLD,
                    advances_goal=True,
                    protects_required_material=True,
                ),
                urgency="normal",
                properties={"owned_quantity": graph.quantity_owned("gw2:item:mystic_coin")},
                explanation="Mystic Coin is required by Aurora and should be reserved for the active goal.",
            )
        )

    return actions


def may_sell_surplus(graph: GraphData, entity_id: str, active_goal_id: str) -> bool:
    gap = calculate_goal_gap(graph, active_goal_id)
    required_entity_ids = {
        item.entity_id for item in gap.completed_requirements + gap.missing_requirements
    }
    entity = graph.entities[entity_id]
    if entity_id in required_entity_ids:
        return False
    if entity.properties.get("legendary_related", False):
        return False
    return bool(entity.properties.get("tradable", False))
