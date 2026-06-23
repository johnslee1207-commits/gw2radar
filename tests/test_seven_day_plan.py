import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.config.settings import get_settings
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_progression_seven_day_plan_exports_deterministic_dag_and_boundaries() -> None:
    temp_dir = Path(".test_tmp") / f"seven-day-plan-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'plan.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        plan_response = client.post(
            "/api/v1/progression/plans/7-day",
            json={"goal_id": "gw2:goal:aurora", "top_k": 5},
        )
        markdown = client.post(
            "/api/v1/progression/plans/7-day/export?format=markdown",
            json={"goal_id": "gw2:goal:aurora", "top_k": 5},
        )
        csv_response = client.post(
            "/api/v1/progression/plans/7-day/export?format=csv",
            json={"goal_id": "gw2:goal:aurora", "top_k": 5},
        )
        json_export = client.post(
            "/api/v1/progression/plans/7-day/export?format=json",
            json={"goal_id": "gw2:goal:aurora", "top_k": 5},
        )
        bad_export = client.post(
            "/api/v1/progression/plans/7-day/export?format=pdf",
            json={"goal_id": "gw2:goal:aurora", "top_k": 5},
        )

        assert plan_response.status_code == 200
        plan = plan_response.json()["data"]["seven_day_plan"]
        assert plan["schema_version"] == "gw2radar.seven_day_plan.v1"
        assert plan["plan_horizon_days"] == 7
        assert plan["node_count"] == 5
        assert plan["edge_count"] == 4
        assert len(plan["days"]) == 7
        assert plan["days"][0]["nodes"][0]["node_id"] == "plan-node-1"
        assert plan["edges"][0]["source_node_id"] == "plan-node-1"
        assert plan["edges"][0]["target_node_id"] == "plan-node-2"
        assert plan["total_estimated_minutes"] >= 5
        assert any("Missing or low-confidence facts" in item for item in plan["assumptions"])
        assert "automatic trading" in plan["deferred_capabilities"]
        assert all(node["status"] == "review_candidate" for node in plan["nodes"])
        assert all("manual player review" in node["manual_action_boundary"] for node in plan["nodes"])

        assert markdown.status_code == 200
        assert "# GW2Radar 7-Day Planning DAG" in markdown.text
        assert "## Dependencies" in markdown.text
        assert "No completion date" in markdown.text
        assert csv_response.status_code == 200
        assert "row_type,day,node_id,action_id,title,action_type" in csv_response.text
        assert "edge,," in csv_response.text
        assert json_export.status_code == 200
        assert json_export.json()["data"]["seven_day_plan"]["node_count"] == 5
        assert bad_export.status_code == 400

        combined = str(plan) + markdown.text + csv_response.text + str(json_export.json())
        assert "secret-key" not in combined.lower()
        assert "guaranteed profit" not in combined.lower()
        assert "automatically buy" not in combined.lower()
        assert "automatically sell" not in combined.lower()
    finally:
        close_database()
        configure_database(get_settings().database_url)
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
