import shutil
import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.db.session import close_database, configure_database


def test_api_uses_persisted_mock_data_after_cache_reset() -> None:
    temp_dir = Path(".test_tmp") / f"api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        first_load = client.post("/mock/load")
        second_load = client.post("/mock/load")

        assert first_load.status_code == 200
        assert second_load.status_code == 200
        assert first_load.json() == second_load.json()

        state.reset_cached_graph()

        goals = client.get("/goals")
        gap = client.get("/goals/gw2:goal:aurora/gap")
        actions = client.post("/goals/gw2:goal:aurora/actions/generate")
        report = client.get("/reports/gw2:goal:aurora/markdown")
        export_package = client.post("/reports/gw2:goal:aurora/export-package")

        assert goals.status_code == 200
        assert goals.json()[0]["id"] == "gw2:goal:aurora"
        assert gap.status_code == 200
        assert any(
            item["entity_id"] == "gw2:currency:unbound_magic"
            for item in gap.json()["missing_requirements"]
        )
        assert actions.status_code == 200
        assert any(action["action_type"] == "do_daily" for action in actions.json())
        assert report.status_code == 200
        assert "## Recommended Actions Today" in report.text
        assert export_package.status_code == 200
        manifest_path = Path(export_package.json()["manifest_path"])
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["schema_version"] == "gw2radar.export_package.v1"
        assert {file["name"] for file in manifest["files"]} == {
            "goal_report.md",
            "goal_gap.csv",
            "recommended_actions.csv",
            "package_manifest.json",
        }
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree("outputs", ignore_errors=True)
