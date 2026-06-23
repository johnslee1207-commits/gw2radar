from sqlalchemy import func, select
from fastapi import APIRouter, Query, Response

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.models import ApiKeySecretModel, RefreshQueueModel
from gw2radar.ops.release_readiness import (
    build_operational_hardening_readiness,
    render_operational_hardening_csv,
    render_operational_hardening_markdown,
)

router = APIRouter(prefix="/api/v1/ops", tags=["ops"])


@router.get("/status", response_model=ApiDataEnvelope)
def get_operational_status() -> ApiDataEnvelope:
    init_db()
    graph = get_graph()
    with db_session.SessionLocal() as session:
        queue_counts = {
            status: count
            for status, count in session.execute(
                select(RefreshQueueModel.status, func.count()).group_by(RefreshQueueModel.status)
            ).all()
        }
        has_api_key = session.get(ApiKeySecretModel, "default") is not None
    return ApiDataEnvelope(
        data={
            "status": "ok",
            "database": "ok",
            "graph": {
                "entities": len(graph.entities),
                "relations": len(graph.relations),
                "player_state": len(graph.player_state),
                "actions": len(graph.actions),
            },
            "refresh_queue": queue_counts,
            "api_key_configured": has_api_key,
            "capabilities": {
                "account_sync": True,
                "public_refresh": True,
                "export_package": True,
                "mock_generation": True,
            },
        }
    )


@router.get("/release-readiness", response_model=None)
def get_operational_release_readiness(
    format: str = Query(default="json", pattern="^(json|markdown|csv)$"),
):
    readiness = build_operational_hardening_readiness()
    if format == "markdown":
        return Response(
            content=render_operational_hardening_markdown(readiness),
            media_type="text/markdown; charset=utf-8",
        )
    if format == "csv":
        return Response(
            content=render_operational_hardening_csv(readiness),
            media_type="text/csv; charset=utf-8",
        )
    return ApiDataEnvelope(data={"release_readiness": readiness.model_dump(mode="json")})
