import shutil
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gw2radar.db.init_db import init_db
from gw2radar.db.repositories import GraphLayerViolation, GraphRepository, validate_graph_layers
from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.inference.action_generator import generate_actions
from gw2radar.inference.goal_gap import calculate_goal_gap
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.relation_types import RelationType


def test_mock_graph_uses_constitutional_layers() -> None:
    graph = build_mock_graph()
    calculate_goal_gap(graph, "gw2:goal:aurora")
    generate_actions(graph, "gw2:goal:aurora")

    assert graph.entities["mock:account:lee"].graph_layer == GraphLayer.PRIVATE_PLAYER_STATE
    assert graph.entities["gw2:goal:aurora"].graph_layer == GraphLayer.PUBLIC_GAME
    assert all(state.graph_layer == GraphLayer.PRIVATE_PLAYER_STATE for state in graph.player_state)
    assert all(
        relation.graph_layer == GraphLayer.PRIVATE_PLAYER_STATE
        for relation in graph.relations
        if relation.predicate == RelationType.OWNED_BY
    )
    assert all(
        relation.graph_layer == GraphLayer.PERSONAL_INTELLIGENCE
        for relation in graph.relations
        if relation.predicate in {RelationType.MISSING_FOR_GOAL, RelationType.ADVANCES_GOAL}
    )
    assert all(action.graph_layer == GraphLayer.PERSONAL_INTELLIGENCE for action in graph.actions)


def test_repository_rejects_private_player_state_in_public_layer() -> None:
    graph = build_mock_graph()
    graph.player_state[0].graph_layer = GraphLayer.PUBLIC_GAME

    with pytest.raises(GraphLayerViolation):
        validate_graph_layers(graph)


def test_repository_round_trip_preserves_graph_layers() -> None:
    temp_dir = Path(".test_tmp") / f"layers-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'layers.db'}")
    init_db(engine)
    session_factory = sessionmaker(bind=engine)

    try:
        graph = build_mock_graph()
        generate_actions(graph, "gw2:goal:aurora")
        with session_factory() as session:
            repo = GraphRepository(session)
            repo.replace_graph(graph)
            loaded = repo.load_graph()

        assert loaded is not None
        assert loaded.entities["mock:account:lee"].graph_layer == GraphLayer.PRIVATE_PLAYER_STATE
        assert loaded.entities["gw2:goal:aurora"].graph_layer == GraphLayer.PUBLIC_GAME
        assert all(action.graph_layer == GraphLayer.PERSONAL_INTELLIGENCE for action in loaded.actions)
        assert any(entity.type == EntityType.GOAL for entity in loaded.entities.values())
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)
