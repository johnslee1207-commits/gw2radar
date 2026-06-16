from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.market_radar import calculate_goal_cost_index, record_price_snapshot
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph
from market_test_helpers import clover_snapshot, mystic_coin_snapshots


def test_goal_cost_index_prices_missing_goal_requirements() -> None:
    temp_dir = Path(".test_tmp") / f"market-index-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'market.db'}")
        init_db()
        graph = build_mock_graph()
        with db_session.SessionLocal() as session:
            record_price_snapshot(session, mystic_coin_snapshots()[-1])
            record_price_snapshot(session, clover_snapshot())
            index = calculate_goal_cost_index(session, graph, "gw2:goal:aurora")

        assert index.total_missing_cost_copper > 0
        assert "gw2:item:mystic_clover" in index.priced_items
        assert "gw2:currency:unbound_magic" in index.unpriced_items
    finally:
        close_database()
