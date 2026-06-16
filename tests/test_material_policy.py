from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.inference.material_policy import generate_material_policy_actions, may_sell_surplus
from gw2radar.ontology.action_types import ActionType


def test_mystic_coin_is_held_for_goal() -> None:
    graph = build_mock_graph()
    actions = generate_material_policy_actions(graph, "gw2:goal:aurora")
    assert any(
        action.action_type == ActionType.HOLD
        and action.target_entity_id == "gw2:item:mystic_coin"
        for action in actions
    )


def test_goal_material_is_not_sell_surplus_candidate() -> None:
    graph = build_mock_graph()
    assert may_sell_surplus(graph, "gw2:item:mystic_coin", "gw2:goal:aurora") is False
