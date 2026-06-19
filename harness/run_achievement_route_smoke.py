"""Achievement route planner smoke harness."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gw2radar.api.main import app  # noqa: E402


def main() -> int:
    client = TestClient(app)
    failures: list[str] = []
    request = {
        "goal_id": "all",
        "available_minutes": 35,
        "unlocked_prerequisite_ids": ["living_world_s3_access", "achievement_api_access"],
        "include_group_content": False,
    }

    page = client.get("/player")
    if page.status_code != 200:
        failures.append(f"player page returned HTTP {page.status_code}")
    elif "Achievement Route Planner" not in page.text:
        failures.append("player page does not expose Achievement Route Planner")

    plan_response = client.post("/api/v1/achievement-routes/plan", json=request)
    plan_payload = _json_response(plan_response, "route plan", failures)
    plan = (((plan_payload or {}).get("data") or {}).get("plan") or {})
    sources_response = client.get("/api/v1/achievement-routes/sources")
    sources_payload = _json_response(sources_response, "route sources", failures)
    reviewed_step_count = (((sources_payload or {}).get("data") or {}).get("reviewed_step_count") or 0)
    if reviewed_step_count < 5:
        failures.append("route source registry did not expose reviewed route steps")
    if plan.get("schema_version") != "gw2radar.achievement_route_plan.v1":
        failures.append("route plan schema_version mismatch")
    if "kb:achievement-routes:reviewed-seed:v1" not in plan.get("source_ids", []):
        failures.append("route plan did not use reviewed source manifest")
    if not plan.get("ready_step_ids"):
        failures.append("route plan did not include ready steps")
    if not plan.get("blocked_step_ids"):
        failures.append("route plan did not include blocked steps")
    if not any("Manual planning only" in item for item in plan.get("safety_boundaries", [])):
        failures.append("route plan did not include manual-planning safety boundary")

    markdown = client.post("/api/v1/achievement-routes/plan/export?format=markdown", json=request)
    if markdown.status_code != 200:
        failures.append(f"route markdown export returned HTTP {markdown.status_code}")
    elif "## Assumptions" not in markdown.text or "guaranteed" in markdown.text.lower():
        failures.append("route markdown export is missing assumptions or contains prohibited guarantee wording")

    csv_response = client.post("/api/v1/achievement-routes/plan/export?format=csv", json=request)
    if csv_response.status_code != 200:
        failures.append(f"route csv export returned HTTP {csv_response.status_code}")
    elif "step_id,title,map_name" not in csv_response.text:
        failures.append("route csv export header mismatch")

    preview_request = _official_preview_request()
    preview_response = client.post("/api/v1/achievement-routes/official-preview", json=preview_request)
    preview_payload = _json_response(preview_response, "official achievement route preview", failures)
    preview = (((preview_payload or {}).get("data") or {}).get("preview") or {})
    if preview.get("manifest", {}).get("source_status") != "draft":
        failures.append("official achievement preview did not remain draft-only")
    if preview.get("candidate_step_count", 0) < 2:
        failures.append("official achievement preview did not create candidate route steps")
    if "official-achievement-2002" not in preview.get("completed_step_ids", []):
        failures.append("official achievement preview did not reflect account completion progress")
    preview_markdown = client.post("/api/v1/achievement-routes/official-preview/export?format=markdown", json=preview_request)
    if preview_markdown.status_code != 200:
        failures.append(f"official preview markdown export returned HTTP {preview_markdown.status_code}")
    elif "Official Achievement Route Preview" not in preview_markdown.text or "guaranteed" in preview_markdown.text.lower():
        failures.append("official preview markdown export failed content or safety checks")

    if failures:
        print("FAIL: GW2Radar achievement route smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: GW2Radar achievement route smoke succeeded")
    return 0


def _json_response(response, label: str, failures: list[str]) -> dict | None:
    if response.status_code != 200:
        failures.append(f"{label} returned HTTP {response.status_code}: {response.text[:240]}")
        return None
    try:
        return response.json()
    except ValueError:
        failures.append(f"{label} did not return JSON")
        return None


def _official_preview_request() -> dict:
    return {
        "source_id": "official:achievement-route-preview:smoke",
        "title": "Smoke official achievement preview",
        "goal_id": "aurora_sample",
        "reviewed_by": "achievement_route_smoke",
        "achievement_details": [
            {
                "id": 2001,
                "name": "Bloodstone Fen Smoke Collection",
                "description": "Complete a collection step in Bloodstone Fen.",
                "requirement": "Review a Bloodstone Fen collection route candidate.",
                "bits": [{"type": "Text", "text": "Smoke bit"}],
            },
            {
                "id": 2002,
                "name": "Daily Ember Bay Smoke",
                "description": "Complete a daily checkpoint in Ember Bay.",
                "requirement": "Daily Ember Bay route candidate.",
                "flags": ["Daily"],
            },
        ],
        "account_achievements": [
            {"id": 2001, "current": 1, "max": 3},
            {"id": 2002, "current": 1, "max": 1},
        ],
    }


if __name__ == "__main__":
    raise SystemExit(main())
