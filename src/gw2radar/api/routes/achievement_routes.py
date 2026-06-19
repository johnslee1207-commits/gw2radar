from fastapi import APIRouter, HTTPException, Query, Response

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.commercial.achievement_route import (
    AchievementRouteRequest,
    build_achievement_route_plan,
    load_reviewed_achievement_route_steps,
    render_achievement_route_csv,
    render_achievement_route_markdown,
)

router = APIRouter(prefix="/api/v1/achievement-routes", tags=["achievement-routes"])


@router.post("/plan", response_model=ApiDataEnvelope)
def post_achievement_route_plan(request: AchievementRouteRequest) -> ApiDataEnvelope:
    plan = build_achievement_route_plan(request)
    return ApiDataEnvelope(data={"plan": plan.model_dump(mode="json")})


@router.get("/sources", response_model=ApiDataEnvelope)
def get_achievement_route_sources() -> ApiDataEnvelope:
    _steps, summaries = load_reviewed_achievement_route_steps()
    return ApiDataEnvelope(
        data={
            "sources": [summary.model_dump(mode="json") for summary in summaries],
            "reviewed_step_count": len(_steps),
        }
    )


@router.post("/plan/export")
def post_achievement_route_export(
    request: AchievementRouteRequest,
    format: str = Query(default="markdown", pattern="^(markdown|csv)$"),
) -> Response:
    plan = build_achievement_route_plan(request)
    if format == "markdown":
        return Response(
            content=render_achievement_route_markdown(plan),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_achievement_route_csv(plan),
            media_type="text/csv; charset=utf-8",
        )
    raise HTTPException(status_code=400, detail="Unsupported achievement route export format.")
