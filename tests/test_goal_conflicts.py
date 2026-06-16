from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.legendary_planner import add_legendary_goal, recompute_legendary_plan
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph
from legendary_test_helpers import add_second_legendary_goal


def test_goal_conflicts_explain_shared_shortfall() -> None:
    temp_dir = Path(".test_tmp") / f"legendary-conflicts-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'planner.db'}")
        init_db()
        graph = build_mock_graph()
        add_second_legendary_goal(graph)
        with db_session.SessionLocal() as session:
            add_legendary_goal(session, graph, "gw2:goal:aurora", priority=10)
            add_legendary_goal(session, graph, "gw2:goal:vision", priority=20)
            result = recompute_legendary_plan(session, graph)

        assert result.conflicts
        assert any("short by" in conflict.explanation for conflict in result.conflicts)
        assert all(conflict.conflict_type == "shared_shortfall" for conflict in result.conflicts)
    finally:
        close_database()
