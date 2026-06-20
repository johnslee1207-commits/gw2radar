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


def test_player_dashboard_returns_best_actions_and_freshness_annotations() -> None:
    temp_dir = Path(".test_tmp") / f"player-dashboard-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'dashboard.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        response = client.get("/api/v1/player/dashboard")
        payload = response.json()["data"]["dashboard"]

        assert response.status_code == 200
        assert payload["schema_version"] == "gw2radar.player_dashboard.v1"
        assert len(payload["today_best_actions"]) >= 1
        assert len(payload["this_week_actions"]) >= 5
        assert any(item["subject"] == "Account Snapshot" for item in payload["data_freshness"])
        assert all(item["safety_boundary"] == "informational_manual_actions_only" for item in payload["today_best_actions"])
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_player_account_value_endpoint_exports_dashboard_ready_snapshot() -> None:
    temp_dir = Path(".test_tmp") / f"player-account-value-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'account-value.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200
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

        response = client.get("/api/v1/player/account-value")
        snapshot = response.json()["data"]["account_value_snapshot"]
        markdown = client.get("/api/v1/player/account-value?format=markdown")
        csv = client.get("/api/v1/player/account-value?format=csv")

        assert response.status_code == 200
        assert snapshot["schema_version"] == "gw2radar.account_value_snapshot.v1"
        assert "summary" in snapshot
        assert isinstance(snapshot["by_location"], list)
        assert isinstance(snapshot["by_status"], list)
        assert "never automates trades" in " ".join(snapshot["safety_boundaries"])
        assert markdown.status_code == 200
        assert "# Account Value Snapshot" in markdown.text
        assert csv.status_code == 200
        assert "holding_id,entity_id,name,location,status" in csv.text
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_legendary_catalog_and_actions_cover_player_guide_goal_choices() -> None:
    temp_dir = Path(".test_tmp") / f"legendary-catalog-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'planner.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        catalog = client.get("/api/v1/legendary/goals/catalog")
        goals = catalog.json()["data"]["goals"]
        goal_names = {goal["display_name"] for goal in goals}
        assert {"Aurora", "Vision", "Conflux", "Ad Infinitum", "Legendary Weapon", "Legendary Armor", "Custom Goal"}.issubset(goal_names)

        created = client.post("/api/v1/legendary/goals", json={"graph_goal_id": "gw2:goal:vision", "priority": 2})
        actions = client.get("/api/v1/legendary/actions")
        plan = actions.json()["data"]["action_plan"]

        assert created.status_code == 200
        assert actions.status_code == 200
        assert plan["today_actions"]
        assert plan["this_week_actions"]
        assert "balanced_path" in plan["route_comparison"]
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_returner_full_report_requires_entitlement_and_exports_artifact() -> None:
    temp_dir = Path(".test_tmp") / f"returner-full-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'reports.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        locked = client.post("/api/v1/returner/report", json={"goal_id": "gw2:goal:aurora"})
        assert locked.status_code == 403

        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "returner_full_report")

        report = client.post("/api/v1/returner/report", json={"goal_id": "gw2:goal:aurora"})
        job = report.json()["data"]["job"]
        artifact = Path(job["artifact_path"])

        assert report.status_code == 200
        assert job["status"] == "succeeded"
        assert artifact.exists()
        text = artifact.read_text(encoding="utf-8")
        assert "Returner Full Recovery Report" in text
        assert "Evidence & Data Freshness" in text
        assert "No gameplay automation" in text
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree("outputs", ignore_errors=True)
