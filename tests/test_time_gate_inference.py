from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.legendary_planner import add_legendary_goal, recompute_legendary_plan
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph


def test_time_gate_inference_marks_currency_and_achievement_requirements() -> None:
    temp_dir = Path(".test_tmp") / f"legendary-timegate-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'planner.db'}")
        init_db()
        graph = build_mock_graph()
        with db_session.SessionLocal() as session:
            add_legendary_goal(session, graph, "gw2:goal:aurora")
            result = recompute_legendary_plan(session, graph)

        gate_ids = {gate.entity_id for gate in result.time_gates}
        assert "gw2:currency:unbound_magic" in gate_ids
        assert "gw2:achievement:aurora_step_x" in gate_ids
    finally:
        close_database()
