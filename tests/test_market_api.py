import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.commercial.report_engine import create_report_entitlement, ensure_default_report_products
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from market_test_helpers import mystic_coin_snapshots


def test_market_api_watchlist_signals_index_and_paid_report() -> None:
    temp_dir = Path(".test_tmp") / f"market-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'market.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        watch = client.post(
            "/api/v1/market/watchlist",
            json={
                "item_id": "gw2:item:mystic_coin",
                "item_name": "Mystic Coin",
                "reason": "Required by active legendary goal.",
            },
        )
        snapshot = client.post("/api/v1/market/snapshots", json=mystic_coin_snapshots()[0].model_dump(mode="json"))
        watchlist = client.get("/api/v1/market/watchlist")
        index = client.get("/api/v1/market/goal-cost-index")
        signals = client.get("/api/v1/market/signals")
        locked = client.post("/api/v1/market/report", json={})

        assert watch.status_code == 200
        assert snapshot.status_code == 200
        assert watchlist.status_code == 200
        assert index.status_code == 200
        assert signals.status_code == 200
        assert signals.json()["data"]["account_value_evidence"]["schema_version"] == "gw2radar.account_value_evidence_bridge.v1"
        assert signals.json()["data"]["account_value_evidence"]["remediation_summary"]
        assert locked.status_code == 403

        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "market_snapshot_report")

        report = client.post("/api/v1/market/report", json={})
        assert report.status_code == 200
        assert report.json()["data"]["job"]["status"] == "succeeded"
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree("outputs", ignore_errors=True)
