from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from gw2radar.api.envelope import ApiError, ApiErrorEnvelope, http_exception_handler

logger = logging.getLogger("gw2radar.api")
from gw2radar.api.routes.acquisition import router as acquisition_router
from gw2radar.api.routes.account import router as account_router
from gw2radar.api.routes.account_sync import router as account_sync_router
from gw2radar.api.routes.achievement_routes import router as achievement_routes_router
from gw2radar.api.routes.actions import router as actions_router
from gw2radar.api.routes.builds import router as builds_router
from gw2radar.api.routes.creator import router as creator_router
from gw2radar.api.routes.goals import router as goals_router
from gw2radar.api.routes.growth import router as growth_router
from gw2radar.api.routes.guilds import guild_router, team_router
from gw2radar.api.routes.kb import router as kb_router
from gw2radar.api.routes.legendary import router as legendary_router
from gw2radar.api.routes.market import router as market_router
from gw2radar.api.routes.ontology import router as ontology_router
from gw2radar.api.routes.ops import router as ops_router
from gw2radar.api.routes.player_dashboard import router as player_dashboard_router
from gw2radar.api.routes.player_os import router as player_os_router
from gw2radar.api.routes.player_ui import router as player_ui_router
from gw2radar.api.routes.progression import router as progression_router
from gw2radar.api.routes.public_refresh import router as public_refresh_router
from gw2radar.api.routes.reports import router as reports_router
from gw2radar.api.routes.returner import router as returner_router
from gw2radar.api.routes.saas import router as saas_router
from gw2radar.api.routes.security import router as security_router
from gw2radar.api.state import load_graph
from gw2radar.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="GW2Radar MVP 0.1", lifespan=lifespan)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("request method=%s path=%s", request.method, request.url.path)
    try:
        response = await call_next(request)
        if response.status_code >= 400:
            logger.warning("response status=%d method=%s path=%s", response.status_code, request.method, request.url.path)
        return response
    except Exception as exc:
        logger.exception("unhandled method=%s path=%s", request.method, request.url.path)
        envelope = ApiErrorEnvelope(error=ApiError(code="internal_error", message="An unexpected error occurred."))
        return JSONResponse(status_code=500, content=envelope.model_dump(mode="json"))
app.mount(
    "/player-ui",
    StaticFiles(directory=Path(__file__).resolve().parents[1] / "ui" / "static"),
    name="player-ui",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/mock/load")
def load_mock_data() -> dict[str, int | str]:
    graph = load_graph()
    return {
        "status": "loaded",
        "entities": len(graph.entities),
        "relations": len(graph.relations),
        "player_state": len(graph.player_state),
    }


app.include_router(goals_router)
app.include_router(legendary_router)
app.include_router(builds_router)
app.include_router(market_router)
app.include_router(growth_router)
app.include_router(guild_router)
app.include_router(team_router)
app.include_router(creator_router)
app.include_router(kb_router)
app.include_router(actions_router)
app.include_router(reports_router)
app.include_router(returner_router)
app.include_router(account_router)
app.include_router(account_sync_router)
app.include_router(achievement_routes_router)
app.include_router(public_refresh_router)
app.include_router(ontology_router)
app.include_router(ops_router)
app.include_router(player_dashboard_router)
app.include_router(player_os_router)
app.include_router(player_ui_router)
app.include_router(security_router)
app.include_router(acquisition_router)
app.include_router(progression_router)
app.include_router(saas_router)
