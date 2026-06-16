from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.market_radar import calculate_price_trends, record_price_snapshot
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from market_test_helpers import mystic_coin_snapshots


def test_price_trend_calculates_direction_and_scores() -> None:
    temp_dir = Path(".test_tmp") / f"market-trend-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'market.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            for snapshot in mystic_coin_snapshots():
                record_price_snapshot(session, snapshot)
            trends = calculate_price_trends(session)

        trend = trends[0]
        assert trend.direction == "up"
        assert trend.delta_from_average_percent > 0
        assert trend.liquidity_score > 0
    finally:
        close_database()
