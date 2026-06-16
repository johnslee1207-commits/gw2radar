from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.report_engine import (
    ReportEntitlementType,
    create_report_entitlement,
    ensure_default_report_products,
    has_report_entitlement,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_report_entitlement_unlocks_full_paid_product() -> None:
    temp_dir = Path(".test_tmp") / f"reports-entitlement-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'reports.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            assert not has_report_entitlement(session, "local-user", "legendary_gap_report")
            entitlement = create_report_entitlement(session, "local-user", "legendary_gap_report")

            assert entitlement.entitlement_type is ReportEntitlementType.FULL
            assert has_report_entitlement(session, "local-user", "legendary_gap_report")
    finally:
        close_database()
