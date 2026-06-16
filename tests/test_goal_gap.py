from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.inference.goal_gap import calculate_goal_gap


def test_goal_gap_matches_aurora_mock_state() -> None:
    graph = build_mock_graph()
    gap = calculate_goal_gap(graph, "gw2:goal:aurora")

    completed = {item.entity_id: item for item in gap.completed_requirements}
    missing = {item.entity_id: item for item in gap.missing_requirements}

    assert completed["gw2:item:mystic_coin"].missing_quantity == 0
    assert missing["gw2:item:mystic_clover"].missing_quantity == 43
    assert missing["gw2:currency:unbound_magic"].missing_quantity == 2200
    assert missing["gw2:achievement:aurora_step_x"].missing_quantity == 1
