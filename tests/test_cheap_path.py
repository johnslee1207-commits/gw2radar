from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.legendary_planner import LegendaryPathType, add_legendary_goal, recompute_legendary_plan
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph


def test_cheap_path_is_recommendation_only() -> None:
    temp_dir = Path(".test_tmp") / f"legendary-cheap-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'planner.db'}")
        init_db()
        graph = build_mock_graph()
        with db_session.SessionLocal() as session:
            add_legendary_goal(session, graph, "gw2:goal:aurora")
            result = recompute_legendary_plan(session, graph)

        assert result.cheap_path
        assert all(step.path_type is LegendaryPathType.CHEAP for step in result.cheap_path)
        assert all("manual acquisition" in step.rationale for step in result.cheap_path)
    finally:
        close_database()
