from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.legendary_planner import (
    add_legendary_goal,
    recompute_legendary_plan,
    render_legendary_planner_report,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph


def test_legendary_pro_report_contains_required_sections_and_boundaries() -> None:
    temp_dir = Path(".test_tmp") / f"legendary-report-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'planner.db'}")
        init_db()
        graph = build_mock_graph()
        with db_session.SessionLocal() as session:
            add_legendary_goal(session, graph, "gw2:goal:aurora")
            result = recompute_legendary_plan(session, graph)

        report = render_legendary_planner_report(result)
        assert "Active Legendary Portfolio" in report
        assert "Cheapest Path" in report
        assert "Fastest Path" in report
        assert "Do-Not-Sell List" in report
        assert "No gameplay automation" in report
        assert "guaranteed-profit" in report
    finally:
        close_database()
