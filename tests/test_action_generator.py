from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.inference.action_generator import generate_actions
from gw2radar.ontology.action_types import ActionType


def test_missing_unbound_magic_generates_daily_action() -> None:
    graph = build_mock_graph()
    actions = generate_actions(graph, "gw2:goal:aurora")
    assert any(action.action_type == ActionType.DO_DAILY for action in actions)


def test_missing_achievement_generates_completion_action() -> None:
    graph = build_mock_graph()
    actions = generate_actions(graph, "gw2:goal:aurora")
    assert any(action.action_type == ActionType.COMPLETE_ACHIEVEMENT for action in actions)


def test_all_actions_have_explanation() -> None:
    graph = build_mock_graph()
    actions = generate_actions(graph, "gw2:goal:aurora")
    assert actions
    assert all(action.explanation for action in actions)


def test_all_actions_have_governance_fields() -> None:
    graph = build_mock_graph()
    actions = generate_actions(graph, "gw2:goal:aurora")

    assert all(action.urgency in {"low", "medium", "high"} for action in actions)
    assert all(action.reason_codes for action in actions)
    assert all(action.evidence_refs for action in actions)
    assert all(action.constraints.get("recommendation_only") is True for action in actions)
