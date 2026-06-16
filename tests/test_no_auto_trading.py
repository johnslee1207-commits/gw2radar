from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.market_radar import build_market_radar_report, record_price_snapshot, render_market_report
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph
from market_test_helpers import mystic_coin_snapshots


def test_market_report_does_not_create_auto_trading_language() -> None:
    temp_dir = Path(".test_tmp") / f"market-no-auto-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'market.db'}")
        init_db()
        graph = build_mock_graph()
        with db_session.SessionLocal() as session:
            for snapshot in mystic_coin_snapshots():
                record_price_snapshot(session, snapshot)
            report = build_market_radar_report(session, graph)
            text = render_market_report(report).lower()

        assert "automated order" not in text
        assert "never places orders" in text
        assert "real-money exchange" in text
    finally:
        close_database()
