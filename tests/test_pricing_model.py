from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.growth import BillingInterval, list_pricing_plans
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_pricing_model_maps_plans_to_report_products() -> None:
    temp_dir = Path(".test_tmp") / f"growth-pricing-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'growth.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            plans = list_pricing_plans(session)

        by_id = {plan.plan_id: plan for plan in plans}
        assert by_id["plan_legendary_once"].product_id == "legendary_planner_pro_report"
        assert by_id["plan_personal_monthly"].billing_interval is BillingInterval.MONTHLY
    finally:
        close_database()
