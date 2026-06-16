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


def test_legendary_pro_api_routes_and_paid_report_gate() -> None:
    temp_dir = Path(".test_tmp") / f"legendary-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'planner.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        created = client.post("/api/v1/legendary/goals", json={"graph_goal_id": "gw2:goal:aurora", "priority": 10})
        portfolio = client.get("/api/v1/legendary/portfolio")
        recomputed = client.post("/api/v1/legendary/recompute")
        do_not_sell = client.get("/api/v1/legendary/do-not-sell")
        locked_report = client.post("/api/v1/legendary/report", json={})

        assert created.status_code == 200
        assert portfolio.status_code == 200
        assert recomputed.status_code == 200
        assert do_not_sell.status_code == 200
        assert locked_report.status_code == 403
        assert do_not_sell.json()["data"]["do_not_sell"]

        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "legendary_planner_pro_report")

        report = client.post("/api/v1/legendary/report", json={})
        assert report.status_code == 200
        assert report.json()["data"]["job"]["status"] == "succeeded"
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree("outputs", ignore_errors=True)
