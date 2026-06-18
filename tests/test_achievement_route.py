from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.commercial.achievement_route import (
    AchievementRouteRequest,
    build_achievement_route_plan,
    render_achievement_route_csv,
    render_achievement_route_markdown,
)


def test_achievement_route_groups_ready_blocked_and_time_gated_steps() -> None:
    plan = build_achievement_route_plan(
        AchievementRouteRequest(
            goal_id="all",
            available_minutes=30,
            unlocked_prerequisite_ids=["living_world_s3_access"],
            include_group_content=False,
        )
    )

    assert "aurora-bloodstone-fen-check" in plan.ready_step_ids
    assert "aurora-ember-bay-daily-token" in plan.time_gated_step_ids
    assert "vision-dragonfall-meta" in plan.blocked_step_ids
    assert plan.segments[0].ready_step_ids
    assert all(action.manual_only for action in plan.next_actions)
    assert any("in-game achievement panel" in assumption for assumption in plan.assumptions)
    assert "guaranteed" not in render_achievement_route_markdown(plan).lower()


def test_achievement_route_markdown_and_csv_exports_are_deterministic() -> None:
    plan = build_achievement_route_plan(
        AchievementRouteRequest(
            goal_id="aurora_sample",
            available_minutes=45,
            unlocked_prerequisite_ids=["living_world_s3_access"],
        )
    )

    markdown = render_achievement_route_markdown(plan)
    csv_text = render_achievement_route_csv(plan)

    assert "# Achievement & Collection Route Plan" in markdown
    assert "## Assumptions" in markdown
    assert "Manual planning only" in markdown
    assert csv_text.splitlines()[0].startswith("step_id,title,map_name")
    assert "aurora-ember-bay-daily-token" in csv_text


def test_achievement_route_api_plan_and_exports() -> None:
    client = TestClient(app)
    request = {
        "goal_id": "all",
        "available_minutes": 40,
        "unlocked_prerequisite_ids": ["living_world_s3_access", "living_world_s4_access"],
        "include_group_content": True,
    }

    planned = client.post("/api/v1/achievement-routes/plan", json=request)
    markdown = client.post("/api/v1/achievement-routes/plan/export?format=markdown", json=request)
    csv_response = client.post("/api/v1/achievement-routes/plan/export?format=csv", json=request)

    assert planned.status_code == 200
    assert planned.json()["data"]["plan"]["schema_version"] == "gw2radar.achievement_route_plan.v1"
    assert markdown.status_code == 200
    assert "Route Segments" in markdown.text
    assert csv_response.status_code == 200
    assert "status,time_gate" in csv_response.text
