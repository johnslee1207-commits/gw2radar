from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.growth import CheckoutRequest, complete_checkout, create_checkout
from gw2radar.commercial.report_engine import has_report_entitlement
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_checkout_completion_grants_report_entitlement() -> None:
    temp_dir = Path(".test_tmp") / f"growth-entitlement-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'growth.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            checkout = create_checkout(session, CheckoutRequest(plan_id="plan_build_fit_once"))
            assert not has_report_entitlement(session, "local-user", "build_fit_report")
            complete_checkout(session, checkout.checkout_session_id)
            assert has_report_entitlement(session, "local-user", "build_fit_report")
    finally:
        close_database()
