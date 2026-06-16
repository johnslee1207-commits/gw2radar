from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.growth import CheckoutRequest, CheckoutStatus, complete_checkout, create_checkout
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_mock_payment_provider_creates_and_completes_checkout() -> None:
    temp_dir = Path(".test_tmp") / f"growth-payment-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'growth.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            checkout = create_checkout(session, CheckoutRequest(plan_id="plan_market_once"))
            completed = complete_checkout(session, checkout.checkout_session_id)

        assert checkout.status is CheckoutStatus.CREATED
        assert completed.status is CheckoutStatus.PAID
        assert completed.checkout_url.startswith("https://checkout.invalid/")
    finally:
        close_database()
