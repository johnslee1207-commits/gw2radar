from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.relation_types import RelationType


def test_can_create_goal_entity() -> None:
    graph = build_mock_graph()
    goal = graph.entities["gw2:goal:aurora"]
    assert goal.type == EntityType.GOAL
    assert goal.canonical_name == "Aurora"


def test_can_create_requires_relation() -> None:
    graph = build_mock_graph()
    assert any(
        relation.subject_id == "gw2:goal:aurora"
        and relation.predicate == RelationType.REQUIRES
        and relation.object_id == "gw2:item:mystic_coin"
        and relation.evidence_id
        for relation in graph.relations
    )


def test_can_create_owned_relation_and_player_state() -> None:
    graph = build_mock_graph()
    assert graph.quantity_owned("gw2:item:mystic_coin") == 120
    assert any(
        relation.predicate == RelationType.OWNED_BY
        and relation.object_id == "gw2:item:mystic_coin"
        for relation in graph.relations
    )
