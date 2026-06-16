from sqlalchemy import func, select
from fastapi import APIRouter

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.api.state import get_graph
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.models import ApiKeySecretModel, RefreshQueueModel

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
