from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.report_engine import ReportTier, list_report_products
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_report_products_seed_default_catalog() -> None:
    temp_dir = Path(".test_tmp") / f"reports-products-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'reports.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            products = list_report_products(session)

        assert {product.product_id for product in products} >= {
            "returner_preview_free",
            "legendary_gap_report",
            "build_fit_report",
            "market_snapshot_report",
        }
        legendary = next(product for product in products if product.product_id == "legendary_gap_report")
        assert legendary.tier is ReportTier.PAID_ONCE
        assert legendary.price_cents == 900
    finally:
        close_database()
