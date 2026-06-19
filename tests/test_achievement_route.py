from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.api.routes import achievement_routes as achievement_route_routes
from gw2radar.commercial.achievement_route import (
    AchievementRouteRequest,
    OfficialAchievementFetchPreviewRequest,
    OfficialAchievementRoutePreviewRequest,
    build_official_achievement_fetch_preview,
    build_achievement_route_plan,
    build_official_achievement_route_preview,
    load_reviewed_achievement_route_steps,
    render_official_achievement_fetch_preview_markdown,
    render_achievement_route_csv,
    render_achievement_route_markdown,
    render_official_achievement_route_preview_markdown,
)
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import GatewayResult


def test_achievement_route_loads_reviewed_source_manifest() -> None:
    steps, summaries = load_reviewed_achievement_route_steps()

    assert len(steps) >= 5
    assert summaries[0].source_status == "reviewed"
    assert summaries[0].step_count >= 5
    assert steps[0].source_id == "kb:achievement-routes:reviewed-seed:v1"
    assert "docs/knowledge_base/official/api_endpoints/achievements.md" in steps[0].evidence_refs


def test_official_achievement_preview_builds_draft_route_manifest() -> None:
    preview = build_official_achievement_route_preview(_official_preview_request())

    assert preview.schema_version == "gw2radar.official_achievement_route_preview.v1"
    assert preview.manifest.source_status == "draft"
    assert preview.candidate_step_count == 3
    assert "official-achievement-1002" in preview.completed_step_ids
    assert preview.manifest.steps[0].source_status == "draft"
    assert preview.manifest.steps[0].prerequisite_ids == ["achievement_api_access"]
    assert any(step.map_name == "Bloodstone Fen" for step in preview.manifest.steps)
    assert any(step.time_gate == "daily" for step in preview.manifest.steps)
    assert "Human review is required" in " ".join(preview.manifest.assumptions)
    assert "guaranteed" not in render_official_achievement_route_preview_markdown(preview).lower()


def test_official_achievement_fetch_preview_orchestrates_gateway_batch() -> None:
    request = _official_fetch_request()
    gateway = FetchPreviewGateway()

    fetch_preview = build_official_achievement_fetch_preview(request, gateway)

    assert gateway.batch_calls == [("/v2/achievements", [1001, 1002, 404])]
    assert fetch_preview.schema_version == "gw2radar.official_achievement_fetch_preview.v1"
    assert fetch_preview.fetched_achievement_ids == [1001, 1002]
    assert fetch_preview.missing_achievement_ids == [404]
    assert fetch_preview.preview.manifest.source_status == "draft"
    assert "official-achievement-1002" in fetch_preview.preview.completed_step_ids
    markdown = render_official_achievement_fetch_preview_markdown(fetch_preview)
    assert "Official Achievement Fetch Preview" in markdown
    assert "guaranteed" not in markdown.lower()


def test_achievement_route_groups_ready_blocked_and_time_gated_steps() -> None:
    plan = build_achievement_route_plan(
        AchievementRouteRequest(
            goal_id="all",
            available_minutes=30,
            unlocked_prerequisite_ids=["living_world_s3_access", "achievement_api_access"],
            include_group_content=False,
        )
    )

    assert "aurora-bloodstone-fen-reviewed-sweep" in plan.ready_step_ids
    assert "aurora-ember-bay-reviewed-daily" in plan.time_gated_step_ids
    assert "vision-dragonfall-reviewed-meta-check" in plan.blocked_step_ids
    assert plan.source_ids == ["kb:achievement-routes:reviewed-seed:v1"]
    assert plan.segments[0].ready_step_ids
    assert all(action.manual_only for action in plan.next_actions)
    assert any("in-game achievement panel" in assumption for assumption in plan.assumptions)
    assert "guaranteed" not in render_achievement_route_markdown(plan).lower()


def test_achievement_route_markdown_and_csv_exports_are_deterministic() -> None:
    plan = build_achievement_route_plan(
        AchievementRouteRequest(
            goal_id="aurora_sample",
            available_minutes=45,
            unlocked_prerequisite_ids=["living_world_s3_access", "achievement_api_access"],
        )
    )

    markdown = render_achievement_route_markdown(plan)
    csv_text = render_achievement_route_csv(plan)

    assert "# Achievement & Collection Route Plan" in markdown
    assert "## Assumptions" in markdown
    assert "## Source Warnings" in markdown
    assert "Manual planning only" in markdown
    assert csv_text.splitlines()[0].startswith("step_id,title,map_name")
    assert "aurora-ember-bay-reviewed-daily" in csv_text
    assert "kb:achievement-routes:reviewed-seed:v1" in csv_text


def test_achievement_route_api_plan_and_exports() -> None:
    client = TestClient(app)
    request = {
        "goal_id": "all",
        "available_minutes": 40,
        "unlocked_prerequisite_ids": ["living_world_s3_access", "living_world_s4_access", "achievement_api_access"],
        "include_group_content": True,
    }

    sources = client.get("/api/v1/achievement-routes/sources")
    planned = client.post("/api/v1/achievement-routes/plan", json=request)
    markdown = client.post("/api/v1/achievement-routes/plan/export?format=markdown", json=request)
    csv_response = client.post("/api/v1/achievement-routes/plan/export?format=csv", json=request)

    assert sources.status_code == 200
    assert sources.json()["data"]["reviewed_step_count"] >= 5
    assert planned.status_code == 200
    assert planned.json()["data"]["plan"]["schema_version"] == "gw2radar.achievement_route_plan.v1"
    assert planned.json()["data"]["plan"]["source_ids"] == ["kb:achievement-routes:reviewed-seed:v1"]
    assert markdown.status_code == 200
    assert "Route Segments" in markdown.text
    assert csv_response.status_code == 200
    assert "status,time_gate" in csv_response.text


def test_official_achievement_preview_api_and_exports() -> None:
    client = TestClient(app)
    request = _official_preview_request().model_dump(mode="json")

    preview = client.post("/api/v1/achievement-routes/official-preview", json=request)
    markdown = client.post("/api/v1/achievement-routes/official-preview/export?format=markdown", json=request)
    json_export = client.post("/api/v1/achievement-routes/official-preview/export?format=json", json=request)

    assert preview.status_code == 200
    payload = preview.json()["data"]["preview"]
    assert payload["manifest"]["source_status"] == "draft"
    assert payload["candidate_step_count"] == 3
    assert payload["manifest"]["steps"][0]["evidence_refs"]
    assert markdown.status_code == 200
    assert "Official Achievement Route Preview" in markdown.text
    assert json_export.status_code == 200
    assert "official:achievement-route-preview:test" in json_export.text


def test_official_achievement_fetch_preview_api_and_exports() -> None:
    original_factory = achievement_route_routes.gateway_factory
    achievement_route_routes.gateway_factory = FetchPreviewGateway
    try:
        client = TestClient(app)
        request = _official_fetch_request().model_dump(mode="json")

        preview = client.post("/api/v1/achievement-routes/official-fetch-preview", json=request)
        markdown = client.post("/api/v1/achievement-routes/official-fetch-preview/export?format=markdown", json=request)
        json_export = client.post("/api/v1/achievement-routes/official-fetch-preview/export?format=json", json=request)

        assert preview.status_code == 200
        payload = preview.json()["data"]["fetch_preview"]
        assert payload["preview"]["manifest"]["source_status"] == "draft"
        assert payload["fetched_achievement_ids"] == [1001, 1002]
        assert payload["missing_achievement_ids"] == [404]
        assert "secret-key" not in str(payload).lower()
        assert markdown.status_code == 200
        assert "Official Achievement Fetch Preview" in markdown.text
        assert json_export.status_code == 200
        assert "official:achievement-route-fetch-preview:test" in json_export.text
    finally:
        achievement_route_routes.gateway_factory = original_factory


def _official_preview_request() -> OfficialAchievementRoutePreviewRequest:
    return OfficialAchievementRoutePreviewRequest(
        source_id="official:achievement-route-preview:test",
        title="Unit official achievement preview",
        goal_id="aurora_sample",
        reviewed_by="unit_test_operator",
        achievement_details=[
            {
                "id": 1001,
                "name": "Bloodstone Fen Sample Collection",
                "description": "Complete a collection step in Bloodstone Fen.",
                "requirement": "Finish the Bloodstone Fen collection check.",
                "bits": [{"type": "Text", "text": "Sample bit"}],
            },
            {
                "id": 1002,
                "name": "Daily Ember Bay Sample",
                "description": "Complete a daily checkpoint in Ember Bay.",
                "requirement": "Daily Ember Bay route review.",
                "flags": ["Daily"],
            },
            {
                "id": 1003,
                "name": "Fractal Sample Collection",
                "description": "Complete a Fractal collection step with a group.",
                "requirement": "Finish a Fractal route checkpoint.",
            },
        ],
        account_achievements=[
            {"id": 1001, "current": 1, "max": 3},
            {"id": 1002, "current": 1, "max": 1},
        ],
    )


def _official_fetch_request() -> OfficialAchievementFetchPreviewRequest:
    return OfficialAchievementFetchPreviewRequest(
        source_id="official:achievement-route-fetch-preview:test",
        title="Unit official fetch preview",
        goal_id="aurora_sample",
        reviewed_by="unit_test_operator",
        achievement_ids=[1001, 1002, 404],
        account_achievements=[
            {"id": 1001, "current": 1, "max": 3},
            {"id": 1002, "current": 1, "max": 1},
        ],
    )


class FetchPreviewGateway:
    def __init__(self) -> None:
        self.batch_calls: list[tuple[str, list[int | str]]] = []

    def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
        self.batch_calls.append((endpoint, list(ids)))
        payload = [
            {
                "id": 1001,
                "name": "Bloodstone Fen Gateway Collection",
                "description": "Complete a collection step in Bloodstone Fen.",
                "requirement": "Finish the Bloodstone Fen gateway route check.",
            },
            {
                "id": 1002,
                "name": "Daily Ember Bay Gateway",
                "description": "Complete a daily checkpoint in Ember Bay.",
                "requirement": "Daily Ember Bay gateway route review.",
                "flags": ["Daily"],
            },
        ]
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id="fetch-preview:test",
            payload=payload,
            evidence_id="evidence:fetch-preview",
        )

    def get(self, endpoint, *, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id="fetch-preview:account",
            payload=[{"id": 1002, "current": 1, "max": 1}],
            evidence_id="evidence:account-achievements",
        )
