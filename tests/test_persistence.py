import shutil
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gw2radar.db.init_db import init_db
from gw2radar.db.repositories import GraphRepository
from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.inference.action_generator import generate_actions


def test_repository_round_trips_mock_graph() -> None:
    temp_dir = Path(".test_tmp") / f"persistence-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'roundtrip.db'}")
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
        assert loaded.entities["gw2:goal:aurora"].canonical_name == "Aurora"
        assert loaded.quantity_owned("gw2:item:mystic_coin") == 120
        assert loaded.actions_for_goal("gw2:goal:aurora")
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)
