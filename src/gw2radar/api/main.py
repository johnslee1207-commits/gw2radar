from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.exceptions import HTTPException as StarletteHTTPException

from gw2radar.api.envelope import http_exception_handler
from gw2radar.api.routes.account import router as account_router
from gw2radar.api.routes.account_sync import router as account_sync_router
from gw2radar.api.routes.actions import router as actions_router
from gw2radar.api.routes.builds import router as builds_router
from gw2radar.api.routes.goals import router as goals_router
from gw2radar.api.routes.growth import router as growth_router
from gw2radar.api.routes.legendary import router as legendary_router
from gw2radar.api.routes.market import router as market_router
from gw2radar.api.routes.ops import router as ops_router
from gw2radar.api.routes.public_refresh import router as public_refresh_router
from gw2radar.api.routes.reports import router as reports_router
from gw2radar.api.routes.security import router as security_router
from gw2radar.api.state import load_graph
from gw2radar.db.init_db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="GW2Radar MVP 0.1", lifespan=lifespan)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)


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
app.include_router(actions_router)
app.include_router(reports_router)
app.include_router(account_router)
app.include_router(account_sync_router)
app.include_router(public_refresh_router)
app.include_router(ops_router)
app.include_router(security_router)
