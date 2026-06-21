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


def test_player_readiness_endpoint_aggregates_commercial_path_checks() -> None:
    temp_dir = Path(".test_tmp") / f"player-readiness-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'readiness.db'}")
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

        response = client.get("/api/v1/player/readiness")
        readiness = response.json()["data"]["readiness"]
        markdown = client.get("/api/v1/player/readiness?format=markdown")
        csv = client.get("/api/v1/player/readiness?format=csv")
        check_ids = {check["check_id"] for check in readiness["checks"]}

        assert response.status_code == 200
        assert readiness["schema_version"] == "gw2radar.player_readiness_summary.v1"
        assert readiness["readiness_label"] in {"ready", "needs_review", "blocked"}
        assert readiness["readiness_score"] >= 0
        assert {"account_sync", "account_value", "legendary_planner", "market_radar", "build_fit_bridge"} <= check_ids
        assert "api_key" not in str(readiness).lower()
        assert "never places trades" in " ".join(readiness["safety_boundaries"])
        assert markdown.status_code == 200
        assert "# Player Readiness Summary" in markdown.text
        assert "## Checks" in markdown.text
        assert "api_key" not in markdown.text.lower()
        assert csv.status_code == 200
        assert "check_id,label,status,evidence,next_action" in csv.text
        assert "summary_key,summary_value" in csv.text
        assert "api_key" not in csv.text.lower()
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_player_readiness_history_records_and_exports_snapshot_comparison() -> None:
    temp_dir = Path(".test_tmp") / f"player-readiness-history-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'readiness-history.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        first = client.post("/api/v1/player/readiness/history?source=test_snapshot")
        second = client.post("/api/v1/player/readiness/history?source=test_snapshot")
        history_response = client.get("/api/v1/player/readiness/history?limit=10")
        history = history_response.json()["data"]["history"]
        markdown = client.get("/api/v1/player/readiness/history?format=markdown")
        csv = client.get("/api/v1/player/readiness/history?format=csv")

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["data"]["snapshot"]["schema_version"] == "gw2radar.player_readiness_snapshot.v1"
        assert history_response.status_code == 200
        assert history["schema_version"] == "gw2radar.player_readiness_history.v1"
        assert len(history["snapshots"]) == 2
        assert history["comparison"]["schema_version"] == "gw2radar.player_readiness_history_comparison.v1"
        assert history["comparison"]["status"] in {"unchanged", "changed", "improved", "regressed"}
        assert "api_key" not in str(history).lower()
        assert markdown.status_code == 200
        assert "# Player Readiness History" in markdown.text
        assert "## Snapshots" in markdown.text
        assert "api_key" not in markdown.text.lower()
        assert csv.status_code == 200
        assert "snapshot_id,created_at,source,readiness_label,readiness_score,check_id,check_status" in csv.text
        assert "comparison_key,comparison_value" in csv.text
        assert "api_key" not in csv.text.lower()
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
        assert snapshot["diagnostics"]["schema_version"] == "gw2radar.account_value_diagnostics.v1"
        assert snapshot["diagnostics"]["source_insights"]
        assert snapshot["diagnostics"]["remediation_actions"]
        assert snapshot["diagnostics"]["price_coverage_percent"] >= 0
        assert any(action["action_id"] in {"refresh_official_prices", "review_value_sources"} for action in snapshot["diagnostics"]["remediation_actions"])
        assert isinstance(snapshot["by_location"], list)
        assert isinstance(snapshot["by_status"], list)
        assert "never automates trades" in " ".join(snapshot["safety_boundaries"])
        assert markdown.status_code == 200
        assert "# Account Value Snapshot" in markdown.text
        assert "## Source Diagnostics" in markdown.text
        assert "## Remediation Actions" in markdown.text
        assert csv.status_code == 200
        assert "holding_id,entity_id,name,location,status" in csv.text
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_player_account_value_history_records_and_exports_snapshot_comparison() -> None:
    temp_dir = Path(".test_tmp") / f"player-account-value-history-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'account-value-history.db'}")
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

        first = client.post("/api/v1/player/account-value/history?source=test_snapshot")
        second = client.post("/api/v1/player/account-value/history?source=test_snapshot")
        history_response = client.get("/api/v1/player/account-value/history?limit=10")
        history = history_response.json()["data"]["history"]
        markdown = client.get("/api/v1/player/account-value/history?format=markdown")
        csv = client.get("/api/v1/player/account-value/history?format=csv")

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["data"]["snapshot"]["schema_version"] == "gw2radar.account_value_history_snapshot.v1"
        assert history_response.status_code == 200
        assert history["schema_version"] == "gw2radar.account_value_history.v1"
        assert len(history["snapshots"]) == 2
        assert history["comparison"]["schema_version"] == "gw2radar.account_value_history_comparison.v1"
        assert history["comparison"]["status"] in {"unchanged", "changed", "improved", "needs_review"}
        assert "api_key" not in str(history).lower()
        assert markdown.status_code == 200
        assert "# Account Value History" in markdown.text
        assert "## Snapshots" in markdown.text
        assert "api_key" not in markdown.text.lower()
        assert csv.status_code == 200
        assert "snapshot_id,created_at,source,total_value_buy_copper" in csv.text
        assert "comparison_key,comparison_value" in csv.text
        assert "api_key" not in csv.text.lower()
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
        planner = client.post("/api/v1/legendary/recompute")
        actions = client.get("/api/v1/legendary/actions")
        planner_payload = planner.json()["data"]["planner"]
        plan = actions.json()["data"]["action_plan"]

        assert created.status_code == 200
        assert planner.status_code == 200
        assert planner_payload["account_value_evidence"]["schema_version"] == "gw2radar.account_value_evidence_bridge.v1"
        assert planner_payload["account_value_evidence"]["remediation_summary"]
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
