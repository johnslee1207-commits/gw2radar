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
from build_fit_helpers import matching_account_gear, sample_build_import


def test_build_fit_api_import_fit_transition_and_paid_report() -> None:
    temp_dir = Path(".test_tmp") / f"build-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'builds.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        imported = client.post("/api/v1/builds/import", json=sample_build_import().model_dump(mode="json"))
        assert imported.status_code == 200
        build_id = imported.json()["data"]["build"]["build_id"]

        listed = client.get("/api/v1/builds")
        fit = client.post(
            "/api/v1/builds/fit",
            json={"build_id": build_id, "account_gear": matching_account_gear().model_dump(mode="json")},
        )
        transition = client.post(
            "/api/v1/builds/transition-plan",
            json={"build_id": build_id, "account_gear": matching_account_gear().model_dump(mode="json")},
        )
        locked = client.post(
            "/api/v1/builds/report",
            json={"build_id": build_id, "account_gear": matching_account_gear().model_dump(mode="json")},
        )

        assert listed.status_code == 200
        assert fit.status_code == 200
        assert fit.json()["data"]["fit"]["score"]["playable_now"] is True
        assert transition.status_code == 200
        assert locked.status_code == 403

        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "build_fit_report")

        report = client.post(
            "/api/v1/builds/report",
            json={"build_id": build_id, "account_gear": matching_account_gear().model_dump(mode="json")},
        )
        assert report.status_code == 200
        assert report.json()["data"]["job"]["status"] == "succeeded"
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree("outputs", ignore_errors=True)
