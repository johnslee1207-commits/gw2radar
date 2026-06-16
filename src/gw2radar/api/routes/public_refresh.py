from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from gw2radar.api import state
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ingest.public_refresh_coordinator import PublicRefreshCoordinator

router = APIRouter(prefix="/api/v1/public/refresh", tags=["public-refresh"])

gateway_factory = Gw2ApiGateway


class PublicRefreshRequest(BaseModel):
    endpoint: str
    ids: list[int] = Field(min_length=1)
    chunk_size: int = Field(default=200, ge=1)


@router.post("")
def enqueue_public_refresh(request: PublicRefreshRequest) -> dict:
    return _with_coordinator(
        lambda coordinator: coordinator.enqueue(
            endpoint=request.endpoint,
            ids=request.ids,
            chunk_size=request.chunk_size,
        )
    )


@router.get("/status")
def get_public_refresh_status() -> dict:
    return _with_coordinator(lambda coordinator: coordinator.status())


@router.post("/drain-one")
def drain_one_public_refresh() -> dict:
    return _with_coordinator(lambda coordinator: coordinator.drain_one())


def _with_coordinator(callback):
    init_db()
    with db_session.SessionLocal() as session:
        coordinator = PublicRefreshCoordinator(
            session=session,
            graph_loader=state.get_graph,
            graph_saver=state.save_graph,
            gateway=gateway_factory(),
        )
        try:
            return callback(coordinator)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
