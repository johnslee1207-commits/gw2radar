#!/usr/bin/env python3
import sys
import shutil
import json
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.db.session import close_database, configure_database
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway


def main() -> int:
    temp_dir = ROOT / ".test_tmp" / f"smoke-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'smoke.db'}")
        state.reset_cached_graph()
        client = TestClient(app)

        health = client.get("/health")
        first_load = client.post("/mock/load")
        second_load = client.post("/mock/load")
        state.reset_cached_graph()
        goals = client.get("/goals")
        gap = client.get("/goals/gw2:goal:aurora/gap")
        actions = client.post("/goals/gw2:goal:aurora/actions/generate")
        report = client.get("/reports/gw2:goal:aurora/markdown")
        export_package = client.post("/reports/gw2:goal:aurora/export-package")
    finally:
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)

    gap_json = gap.json() if gap.status_code == 200 else {}
    actions_json = actions.json() if actions.status_code == 200 else []
    export_json = export_package.json() if export_package.status_code == 200 else {}
    manifest_path = ROOT / export_json.get("manifest_path", "__missing_manifest__")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.is_file() else {}
    checks = [
        (ROOT / "GW2RADAR_PROJECT_CONSTITUTION.md").exists(),
        (ROOT / "GW2RADAR_API_ACCESS_GOVERNANCE.md").exists(),
        Gw2ApiGateway is not None,
        health.status_code == 200 and health.json() == {"status": "ok"},
        first_load.status_code == 200,
        second_load.status_code == 200,
        first_load.json() == second_load.json(),
        goals.status_code == 200,
        any(goal["id"] == "gw2:goal:aurora" for goal in goals.json()),
        gap.status_code == 200 and gap_json.get("goal_name") == "Aurora",
        any(
            item["entity_id"] == "gw2:item:mystic_coin"
            for item in gap_json.get("completed_requirements", [])
        ),
        any(
            item["entity_id"] == "gw2:item:mystic_clover"
            for item in gap_json.get("missing_requirements", [])
        ),
        actions.status_code == 200,
        any(action["action_type"] == "do_daily" for action in actions_json),
        any(action["action_type"] == "complete_achievement" for action in actions_json),
        all(action.get("explanation") for action in actions_json),
        report.status_code == 200,
        "## Active Goal" in report.text,
        "## Missing Requirements" in report.text,
        "## Recommended Actions Today" in report.text,
        export_package.status_code == 200,
        manifest.get("schema_version") == "gw2radar.export_package.v1",
        {file["name"] for file in manifest.get("files", [])}
        == {"goal_report.md", "goal_gap.csv", "recommended_actions.csv", "package_manifest.json"},
    ]
    shutil.rmtree(ROOT / "outputs", ignore_errors=True)
    if not all(checks):
        print("FAIL: GW2Radar MVP 0.1 smoke harness checks failed")
        return 1
    print("PASS: GW2Radar MVP 0.1 mock legendary goal loop succeeded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
