import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.commercial.market_radar import PriceSnapshotInput, record_price_snapshot
from gw2radar.commercial.report_engine import create_report_entitlement, ensure_default_report_products
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_models import KnowledgeDomain, KnowledgeReviewStatus, KnowledgeRuleInput
from gw2radar.kb.kb_repository import create_rule
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

        with db_session.SessionLocal() as session:
            record_price_snapshot(
                session,
                PriceSnapshotInput(
                    item_id="gw2:item:mystic_coin",
                    item_name="Mystic Coin",
                    buy_price_copper=12000,
                    sell_price_copper=12500,
                    volume=10000,
                ),
            )
            create_rule(
                session,
                KnowledgeRuleInput(
                    name="Power relic upgrade effect evidence",
                    domain=KnowledgeDomain.BUILD,
                    condition="relic_effect_family:power_damage",
                    recommendation="Power relic entries can support power_damage upgrade-effect explanations.",
                    action_type="explain_upgrade_effect",
                    priority_delta=0.0,
                    explanation_template="Reviewed KB evidence maps power relic text to power_damage.",
                    evidence_refs=["kb:manual:power-relic"],
                    confidence=0.8,
                    review_status=KnowledgeReviewStatus.REVIEWED,
                    enabled=True,
                ),
            )

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
        assert fit.json()["data"]["fit"]["upgrade_effects"][0]["evidence_source"] == "reviewed_kb_rule"
        assert fit.json()["data"]["fit"]["transition_plan"]["value_context"]
        assert any(
            "reserved for active goals" in note
            for note in fit.json()["data"]["fit"]["transition_plan"]["reserved_goal_notes"]
        )
        assert transition.status_code == 200
        assert transition.json()["data"]["transition_plan"]["value_context"]
        assert transition.json()["data"]["transition_plan"]["reserved_goal_notes"]
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
