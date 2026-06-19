"""Achievement route planner smoke harness."""

from __future__ import annotations

import sys
from shutil import rmtree
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gw2radar.api.main import app  # noqa: E402
from gw2radar.api.routes import achievement_routes as achievement_route_routes  # noqa: E402
from gw2radar.ingest.gateway_status import GatewayStatus  # noqa: E402
from gw2radar.ingest.gw2_api_gateway import GatewayResult  # noqa: E402


def main() -> int:
    original_gateway_factory = achievement_route_routes.gateway_factory
    original_source_root = achievement_route_routes.source_root
    original_audit_root = achievement_route_routes.audit_root
    achievement_route_routes.gateway_factory = FetchPreviewGateway
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
    elif "Operator review gate" not in page.text or "Promote reviewed" not in page.text:
        failures.append("player page does not expose the achievement route operator review gate")

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

    fetch_request = _official_fetch_request()
    fetch_response = client.post("/api/v1/achievement-routes/official-fetch-preview", json=fetch_request)
    fetch_payload = _json_response(fetch_response, "official achievement fetch preview", failures)
    fetch_preview = (((fetch_payload or {}).get("data") or {}).get("fetch_preview") or {})
    if fetch_preview.get("preview", {}).get("manifest", {}).get("source_status") != "draft":
        failures.append("official fetch preview did not remain draft-only")
    if fetch_preview.get("fetched_achievement_ids") != [2001, 2002]:
        failures.append("official fetch preview did not fetch expected achievement ids")
    if fetch_preview.get("missing_achievement_ids") != [9999]:
        failures.append("official fetch preview did not report missing ids")
    fetch_markdown = client.post("/api/v1/achievement-routes/official-fetch-preview/export?format=markdown", json=fetch_request)
    if fetch_markdown.status_code != 200:
        failures.append(f"official fetch preview markdown export returned HTTP {fetch_markdown.status_code}")
    elif "Official Achievement Fetch Preview" not in fetch_markdown.text or "guaranteed" in fetch_markdown.text.lower():
        failures.append("official fetch preview markdown export failed content or safety checks")

    temp_source_root = ROOT / ".test_tmp" / "achievement-route-smoke-promotion"
    temp_audit_root = ROOT / ".test_tmp" / "achievement-route-smoke-audit"
    if temp_source_root.exists():
        rmtree(temp_source_root)
    if temp_audit_root.exists():
        rmtree(temp_audit_root)
    temp_source_root.mkdir(parents=True, exist_ok=True)
    temp_audit_root.mkdir(parents=True, exist_ok=True)
    achievement_route_routes.source_root = temp_source_root
    achievement_route_routes.audit_root = temp_audit_root
    review = {
        "confirmed_reviewed": True,
        "reviewer": "achievement_route_smoke",
        "reviewed_source_id": "kb:achievement-routes:smoke-official-fetch:v1",
        "review_notes": ["Smoke reviewer confirmed fetched official achievement candidates."],
    }
    blocked_promotion = client.post(
        "/api/v1/achievement-routes/official-fetch-preview/promote-reviewed",
        json={"request": fetch_request, "review": {**review, "confirmed_reviewed": False}},
    )
    if blocked_promotion.status_code != 400:
        failures.append("official fetch promotion did not require reviewed confirmation")
    promotion_response = client.post(
        "/api/v1/achievement-routes/official-fetch-preview/promote-reviewed",
        json={"request": fetch_request, "review": review},
    )
    promotion_payload = _json_response(promotion_response, "official achievement reviewed promotion", failures)
    promotion = (((promotion_payload or {}).get("data") or {}).get("promotion") or {})
    if promotion.get("manifest", {}).get("source_status") != "reviewed":
        failures.append("official fetch promotion did not create a reviewed manifest")
    if promotion.get("planner_ingestion_status") != "ready":
        failures.append("official fetch promotion was not marked ready for planner ingestion")
    audit_record = (((promotion_payload or {}).get("data") or {}).get("audit_record") or {})
    if audit_record.get("reviewer") != "achievement_route_smoke":
        failures.append("official fetch promotion did not return a reviewer audit record")
    audit_response = client.get("/api/v1/achievement-routes/promotion-audit?reviewer=achievement_route_smoke&limit=5")
    audit_payload = _json_response(audit_response, "achievement route promotion audit", failures)
    audit_records = ((((audit_payload or {}).get("data") or {}).get("audit") or {}).get("records") or [])
    if not audit_records:
        failures.append("achievement route promotion audit did not list the promotion event")
    audit_markdown = client.get("/api/v1/achievement-routes/promotion-audit?reviewer=achievement_route_smoke&format=markdown")
    if audit_markdown.status_code != 200 or "# Achievement Route Promotion Audit" not in audit_markdown.text:
        failures.append("achievement route promotion audit markdown export failed")
    audit_csv = client.get("/api/v1/achievement-routes/promotion-audit?reviewer=achievement_route_smoke&format=csv")
    if audit_csv.status_code != 200 or "event_id,occurred_at,reviewer,source_id" not in audit_csv.text:
        failures.append("achievement route promotion audit csv export failed")
    readiness_response = client.get("/api/v1/achievement-routes/release-readiness")
    readiness_payload = _json_response(readiness_response, "achievement route release readiness", failures)
    readiness = (((readiness_payload or {}).get("data") or {}).get("readiness") or {})
    if readiness.get("promotion_audit_count", 0) < 1:
        failures.append("achievement route release readiness did not include promotion audit coverage")
    if readiness.get("reviewed_step_count", 0) < 2:
        failures.append("achievement route release readiness did not count reviewed route steps")
    readiness_markdown = client.get("/api/v1/achievement-routes/release-readiness?format=markdown")
    if readiness_markdown.status_code != 200 or "# Achievement Route Release Readiness" not in readiness_markdown.text:
        failures.append("achievement route release readiness markdown export failed")
    readiness_csv = client.get("/api/v1/achievement-routes/release-readiness?format=csv")
    if readiness_csv.status_code != 200 or "ready,maturity_label,readiness_score" not in readiness_csv.text:
        failures.append("achievement route release readiness csv export failed")
    quality_response = client.get("/api/v1/achievement-routes/source-quality")
    quality_payload = _json_response(quality_response, "achievement route source quality", failures)
    quality = (((quality_payload or {}).get("data") or {}).get("quality") or {})
    if not quality.get("step_reviews"):
        failures.append("achievement route source quality did not review promoted steps")
    if "9999" not in str(quality) or not quality.get("remediation"):
        failures.append("achievement route source quality did not report missing official achievement id remediation")
    quality_markdown = client.get("/api/v1/achievement-routes/source-quality?format=markdown")
    if quality_markdown.status_code != 200 or "# Achievement Route Source Quality Review" not in quality_markdown.text:
        failures.append("achievement route source quality markdown export failed")
    quality_csv = client.get("/api/v1/achievement-routes/source-quality?format=csv")
    if quality_csv.status_code != 200 or "step_id,source_id,quality_score" not in quality_csv.text:
        failures.append("achievement route source quality csv export failed")
    remediation_response = client.get("/api/v1/achievement-routes/source-quality/remediation-queue")
    remediation_payload = _json_response(remediation_response, "achievement route remediation queue", failures)
    remediation = (((remediation_payload or {}).get("data") or {}).get("remediation_queue") or {})
    if remediation.get("p0_count", 0) < 1 or not remediation.get("items"):
        failures.append("achievement route remediation queue did not expose missing official id repair items")
    remediation_markdown = client.get("/api/v1/achievement-routes/source-quality/remediation-queue?format=markdown")
    if remediation_markdown.status_code != 200 or "# Achievement Route Remediation Queue" not in remediation_markdown.text:
        failures.append("achievement route remediation queue markdown export failed")
    remediation_csv = client.get("/api/v1/achievement-routes/source-quality/remediation-queue?format=csv")
    if remediation_csv.status_code != 200 or "item_id,priority,remediation_type" not in remediation_csv.text:
        failures.append("achievement route remediation queue csv export failed")
    remediation_item_id = (remediation.get("items") or [{}])[0].get("item_id")
    review_response = client.post(
        "/api/v1/achievement-routes/source-quality/remediation-queue/review",
        json={
            "item_id": remediation_item_id,
            "status": "acknowledged",
            "reviewer": "smoke_operator",
            "notes": ["Smoke acknowledged missing official id remediation before release."],
            "evidence_refs": ["official:/v2/achievements"],
            "confirmed_manual_review": True,
        },
    )
    review_payload = _json_response(review_response, "achievement route remediation review", failures)
    review_record = (((review_payload or {}).get("data") or {}).get("remediation_review") or {})
    if review_record.get("status") != "acknowledged" or review_record.get("reviewer") != "smoke_operator":
        failures.append("achievement route remediation review action did not write expected audit metadata")
    review_audit = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/review-audit?reviewer=smoke_operator")
    review_audit_payload = _json_response(review_audit, "achievement route remediation review audit", failures)
    review_records = (((review_audit_payload or {}).get("data") or {}).get("remediation_review_audit") or {}).get("records", [])
    if not review_records:
        failures.append("achievement route remediation review audit did not list reviewed item")
    review_audit_markdown = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/review-audit?format=markdown")
    if review_audit_markdown.status_code != 200 or "# Achievement Route Remediation Review Audit" not in review_audit_markdown.text:
        failures.append("achievement route remediation review audit markdown export failed")
    review_audit_csv = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/review-audit?format=csv")
    if review_audit_csv.status_code != 200 or "event_id,occurred_at,reviewer,status" not in review_audit_csv.text:
        failures.append("achievement route remediation review audit csv export failed")
    promoted_sources = client.get("/api/v1/achievement-routes/sources")
    promoted_sources_payload = _json_response(promoted_sources, "promoted route sources", failures)
    promoted_reviewed_step_count = (((promoted_sources_payload or {}).get("data") or {}).get("reviewed_step_count") or 0)
    if promoted_reviewed_step_count != 2:
        failures.append("promoted reviewed source did not expose expected route steps")
    promoted_plan = client.post(
        "/api/v1/achievement-routes/plan",
        json={
            "goal_id": "aurora_sample",
            "available_minutes": 35,
            "unlocked_prerequisite_ids": ["achievement_api_access"],
        },
    )
    promoted_plan_payload = _json_response(promoted_plan, "promoted route plan", failures)
    promoted_source_ids = (((promoted_plan_payload or {}).get("data") or {}).get("plan") or {}).get("source_ids", [])
    if promoted_source_ids != ["kb:achievement-routes:smoke-official-fetch:v1"]:
        failures.append("route planner did not ingest promoted reviewed source manifest")

    if failures:
        achievement_route_routes.gateway_factory = original_gateway_factory
        achievement_route_routes.source_root = original_source_root
        achievement_route_routes.audit_root = original_audit_root
        print("FAIL: GW2Radar achievement route smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    achievement_route_routes.gateway_factory = original_gateway_factory
    achievement_route_routes.source_root = original_source_root
    achievement_route_routes.audit_root = original_audit_root
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


def _official_fetch_request() -> dict:
    return {
        "source_id": "official:achievement-route-fetch-preview:smoke",
        "title": "Smoke official achievement fetch preview",
        "goal_id": "aurora_sample",
        "reviewed_by": "achievement_route_smoke",
        "achievement_ids": [2001, 2002, 9999],
        "account_achievements": [
            {"id": 2001, "current": 1, "max": 3},
            {"id": 2002, "current": 1, "max": 1},
        ],
    }


class FetchPreviewGateway:
    def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
        payload = [
            {
                "id": 2001,
                "name": "Bloodstone Fen Smoke Fetch",
                "description": "Complete a collection step in Bloodstone Fen.",
                "requirement": "Review a Bloodstone Fen fetched route candidate.",
            },
            {
                "id": 2002,
                "name": "Daily Ember Bay Smoke Fetch",
                "description": "Complete a daily checkpoint in Ember Bay.",
                "requirement": "Daily Ember Bay fetched route candidate.",
                "flags": ["Daily"],
            },
        ]
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id="smoke:fetch-preview",
            payload=payload,
            evidence_id="evidence:smoke-fetch-preview",
        )

    def get(self, endpoint, *, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id="smoke:account-achievements",
            payload=[{"id": 2002, "current": 1, "max": 1}],
            evidence_id="evidence:smoke-account-achievements",
        )


if __name__ == "__main__":
    raise SystemExit(main())
