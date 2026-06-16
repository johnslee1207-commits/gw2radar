import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.api.routes import public_refresh as public_refresh_route
from gw2radar.db.session import close_database, configure_database
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import GatewayResult
from gw2radar.ontology.graph_layers import GraphLayer


class PublicRefreshGateway:
    def __init__(self) -> None:
        self.batch_calls = []

    def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
        self.batch_calls.append((endpoint, list(ids)))
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id=f"req:{endpoint}:{len(self.batch_calls)}",
            payload=[
                {
                    "id": item_id,
                    "name": f"{endpoint.rsplit('/', 1)[-1].title()} {item_id}",
                    "rarity": "Basic",
                    "level": 0,
                }
                for item_id in ids
            ],
            evidence_id=f"evidence:{endpoint}:{len(self.batch_calls)}",
        )


def test_public_static_refresh_enqueue_status_and_drain() -> None:
    temp_dir, original_factory, gateway = _setup_temp_api("public-refresh")
    try:
        client = TestClient(app)
        queued = client.post(
            "/api/v1/public/refresh",
            json={"endpoint": "/v2/items", "ids": [3, 1, 3, 2], "chunk_size": 2},
        )
        status_before = client.get("/api/v1/public/refresh/status")
        drained = client.post("/api/v1/public/refresh/drain-one")
        status_after = client.get("/api/v1/public/refresh/status")

        assert queued.status_code == 200
        assert queued.json()["status"] == "queued"
        assert queued.json()["ids"] == [1, 2, 3]
        assert status_before.json()["counts"]["queued"] == 1
        assert drained.json()["status"] == "succeeded"
        assert drained.json()["updated_entities"] == 3
        assert drained.json()["chunks"] == 2
        assert status_after.json()["counts"]["succeeded"] == 1
        assert gateway.batch_calls == [("/v2/items", [1, 2]), ("/v2/items", [3])]

        state.reset_cached_graph()
        graph = state.get_graph()
        assert graph.entities["gw2:item:1"].graph_layer == GraphLayer.PUBLIC_GAME
        assert graph.entities["gw2:item:1"].properties["evidence_id"].startswith("evidence:/v2/items")
        refreshed_entities = [
            entity for entity in graph.entities.values() if entity.id in {"gw2:item:1", "gw2:item:2", "gw2:item:3"}
        ]
        assert all(entity.graph_layer == GraphLayer.PUBLIC_GAME for entity in refreshed_entities)
    finally:
        _teardown_temp_api(temp_dir, original_factory)


def test_public_static_refresh_rejects_unsupported_endpoint() -> None:
    temp_dir, original_factory, _gateway = _setup_temp_api("public-refresh-bad")
    try:
        response = TestClient(app).post(
            "/api/v1/public/refresh",
            json={"endpoint": "/v2/account", "ids": [1]},
        )
        assert response.status_code == 400
        assert response.json()["ok"] is False
        assert "Unsupported public static endpoint" in response.json()["error"]["message"]
    finally:
        _teardown_temp_api(temp_dir, original_factory)


def test_public_static_refresh_drain_one_idle_without_task() -> None:
    temp_dir, original_factory, _gateway = _setup_temp_api("public-refresh-idle")
    try:
        response = TestClient(app).post("/api/v1/public/refresh/drain-one")
        assert response.json() == {"status": "idle"}
    finally:
        _teardown_temp_api(temp_dir, original_factory)


def _setup_temp_api(name: str):
    temp_dir = Path(".test_tmp") / f"{name}-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    configure_database(f"sqlite:///{temp_dir / 'public.db'}")
    state.reset_cached_graph()
    original_factory = public_refresh_route.gateway_factory
    gateway = PublicRefreshGateway()
    public_refresh_route.gateway_factory = lambda: gateway
    return temp_dir, original_factory, gateway


def _teardown_temp_api(temp_dir: Path, original_factory) -> None:
    public_refresh_route.gateway_factory = original_factory
    close_database()
    state.reset_cached_graph()
    shutil.rmtree(temp_dir, ignore_errors=True)
