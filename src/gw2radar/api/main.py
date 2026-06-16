from fastapi import FastAPI

from gw2radar.api.routes.actions import router as actions_router
from gw2radar.api.routes.goals import router as goals_router
from gw2radar.api.routes.reports import router as reports_router
from gw2radar.api.state import load_graph

app = FastAPI(title="GW2Radar MVP 0.1")


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
app.include_router(actions_router)
app.include_router(reports_router)
