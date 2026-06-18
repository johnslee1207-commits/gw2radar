from fastapi import APIRouter

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph
from gw2radar.commercial.player_intelligence import (
    build_data_freshness_annotations,
    build_player_dashboard_plan,
)

router = APIRouter(prefix="/api/v1/player", tags=["player-dashboard"])


@router.get("/dashboard", response_model=ApiDataEnvelope)
def get_player_dashboard() -> ApiDataEnvelope:
    graph = get_graph()
    plan = build_player_dashboard_plan(graph)
    return ApiDataEnvelope(data={"dashboard": plan.model_dump(mode="json")})


@router.get("/freshness-annotations", response_model=ApiDataEnvelope)
def get_player_freshness_annotations() -> ApiDataEnvelope:
    graph = get_graph()
    return ApiDataEnvelope(
        data={"annotations": [item.model_dump(mode="json") for item in build_data_freshness_annotations(graph)]}
    )
