from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.legendary_planner import add_legendary_goal, recompute_legendary_plan
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph
from legendary_test_helpers import add_second_legendary_goal


def test_do_not_sell_policy_reserves_materials_across_active_goals() -> None:
    temp_dir = Path(".test_tmp") / f"legendary-dns-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'planner.db'}")
        init_db()
        graph = build_mock_graph()
        add_second_legendary_goal(graph)
        with db_session.SessionLocal() as session:
            add_legendary_goal(session, graph, "gw2:goal:aurora")
            add_legendary_goal(session, graph, "gw2:goal:vision")
            result = recompute_legendary_plan(session, graph)

        mystic_coin = next(item for item in result.do_not_sell if item.entity_id == "gw2:item:mystic_coin")
        assert mystic_coin.policy == "do_not_sell"
        assert set(mystic_coin.reserved_for_goal_ids) == {"gw2:goal:aurora", "gw2:goal:vision"}
    finally:
        close_database()
