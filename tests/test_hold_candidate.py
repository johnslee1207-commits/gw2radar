from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.market_radar import MarketSignalType, infer_market_signals, record_price_snapshot
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph
from market_test_helpers import mystic_coin_snapshots


def test_hold_candidate_for_required_owned_material() -> None:
    temp_dir = Path(".test_tmp") / f"market-hold-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'market.db'}")
        init_db()
        graph = build_mock_graph()
        with db_session.SessionLocal() as session:
            record_price_snapshot(session, mystic_coin_snapshots()[0])
            signals = infer_market_signals(session, graph, "gw2:goal:aurora")

        assert any(
            signal.item_id == "gw2:item:mystic_coin" and signal.signal_type is MarketSignalType.HOLD
            for signal in signals
        )
    finally:
        close_database()
