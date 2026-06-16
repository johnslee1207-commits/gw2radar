from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.market_radar import record_price_snapshot
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from market_test_helpers import mystic_coin_snapshots


def test_price_snapshot_persists_manual_observation() -> None:
    temp_dir = Path(".test_tmp") / f"market-snapshot-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'market.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            snapshot = record_price_snapshot(session, mystic_coin_snapshots()[0])

        assert snapshot.item_id == "gw2:item:mystic_coin"
        assert snapshot.sell_price_copper == 12500
        assert snapshot.source == "manual_snapshot"
    finally:
        close_database()
