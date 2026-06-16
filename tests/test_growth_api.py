from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.commercial.report_engine import has_report_entitlement
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_growth_api_pages_pricing_checkout_and_entitlement() -> None:
    temp_dir = Path(".test_tmp") / f"growth-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'growth.db'}")
        init_db()
        client = TestClient(app)

        pages = client.get("/api/v1/growth/pages")
        privacy = client.get("/api/v1/growth/pages/privacy")
        pricing = client.get("/api/v1/growth/pricing")
        checkout = client.post("/api/v1/growth/checkout", json={"plan_id": "plan_legendary_once"})

        assert pages.status_code == 200
        assert privacy.status_code == 200
        assert pricing.status_code == 200
        assert checkout.status_code == 200
        checkout_id = checkout.json()["data"]["checkout"]["checkout_session_id"]
        completed = client.post(f"/api/v1/growth/checkout/{checkout_id}/complete")

        assert completed.status_code == 200
        with db_session.SessionLocal() as session:
            assert has_report_entitlement(session, "local-user", "legendary_planner_pro_report")
    finally:
        close_database()
