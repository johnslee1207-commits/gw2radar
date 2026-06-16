from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.legendary_planner import add_legendary_goal, get_portfolio
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph


def test_goal_portfolio_persists_legendary_goal() -> None:
    temp_dir = Path(".test_tmp") / f"legendary-portfolio-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'planner.db'}")
        init_db()
        graph = build_mock_graph()
        with db_session.SessionLocal() as session:
            goal = add_legendary_goal(session, graph, "gw2:goal:aurora", priority=10)
            portfolio = get_portfolio(session)

        assert goal.display_name == "Aurora"
        assert portfolio.goals[0].graph_goal_id == "gw2:goal:aurora"
        assert portfolio.goals[0].priority == 10
    finally:
        close_database()
