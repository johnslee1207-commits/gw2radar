import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.api.routes import account_sync as account_sync_route
from gw2radar.db.session import close_database, configure_database
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import GatewayResult
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer


class AccountSyncGateway:
    payloads = {
        "/v2/account": {"name": "Test.1234", "world": 1001},
        "/v2/characters": ["Hero One"],
        "/v2/account/wallet": [{"id": 1, "value": 42}],
        "/v2/account/materials": [{"id": 19721, "count": 7}],
        "/v2/account/bank": [{"id": 19722, "count": 2}],
        "/v2/account/achievements": [{"id": 999, "current": 1, "max": 1}],
    }

    def _fetch_tokeninfo(self, api_key, *, request_id):
        return {
            "name": "Unit Test",
            "permissions": ["account", "characters", "wallet", "inventories", "progression"],
        }

    def get(self, endpoint, *, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id=f"req:{endpoint}",
            payload=self.payloads[endpoint],
            evidence_id=f"evidence:{endpoint}",
        )


class MissingWalletScopeGateway(AccountSyncGateway):
    def _fetch_tokeninfo(self, api_key, *, request_id):
        return {"name": "Unit Test", "permissions": ["account", "characters", "inventories", "progression"]}


def test_account_sync_requires_configured_key() -> None:
    temp_dir, original_factory = _setup_temp_api("sync-no-key")
    try:
        response = TestClient(app).post("/api/v1/account/sync")
        assert response.status_code == 400
        assert "API key is not configured" in response.json()["detail"]
    finally:
        _teardown_temp_api(temp_dir, original_factory)


def test_account_sync_enqueue_status_and_no_key_leakage() -> None:
    temp_dir, original_factory = _setup_temp_api("sync-enqueue")
    raw_key = "12345678-abcdef-secret-key"
    try:
        client = TestClient(app)
        assert client.put("/account/api-key", json={"api_key": raw_key}).status_code == 200
        response = client.post("/api/v1/account/sync")
        status = client.get("/api/v1/account/sync/status")

        assert response.status_code == 200
        assert response.json()["status"] == "queued"
        assert response.json()["task_type"] == "account_snapshot_sync"
        assert raw_key not in str(response.json())
        assert status.json()["counts"]["queued"] == 1
        assert raw_key not in str(status.json())
    finally:
        _teardown_temp_api(temp_dir, original_factory)


def test_account_sync_scope_validation_blocks_enqueue() -> None:
    temp_dir, original_factory = _setup_temp_api("sync-scope", gateway_factory=MissingWalletScopeGateway)
    try:
        client = TestClient(app)
        assert client.put("/account/api-key", json={"api_key": "12345678-abcdef-secret-key"}).status_code == 200
        response = client.post("/api/v1/account/sync")

        assert response.status_code == 400
        assert "wallet" in response.json()["detail"]
    finally:
        _teardown_temp_api(temp_dir, original_factory)


def test_account_sync_drain_one_persists_private_layer_snapshot() -> None:
    temp_dir, original_factory = _setup_temp_api("sync-drain")
    try:
        client = TestClient(app)
        assert client.put("/account/api-key", json={"api_key": "12345678-abcdef-secret-key"}).status_code == 200
        queued = client.post("/api/v1/account/sync")
        drained = client.post("/api/v1/account/sync/drain-one")
        status = client.get("/api/v1/account/sync/status")

        assert queued.status_code == 200
        assert drained.status_code == 200
        assert drained.json()["status"] == "succeeded"
        assert drained.json()["updated_player_state"] == 5
        assert status.json()["counts"]["succeeded"] == 1

        state.reset_cached_graph()
        graph = state.get_graph()
        assert graph.entities["gw2:account:Test.1234"].graph_layer == GraphLayer.PRIVATE_PLAYER_STATE
        assert graph.entities["gw2:character:Hero One"].type == EntityType.CHARACTER
        assert graph.entities["gw2:character:Hero One"].graph_layer == GraphLayer.PRIVATE_PLAYER_STATE
        assert all(player_state.graph_layer == GraphLayer.PRIVATE_PLAYER_STATE for player_state in graph.player_state)
        assert all(
            relation.graph_layer == GraphLayer.PRIVATE_PLAYER_STATE
            for relation in graph.relations
            if relation.subject_id == "gw2:account:Test.1234"
        )
    finally:
        _teardown_temp_api(temp_dir, original_factory)


def test_account_sync_drain_one_idle_without_task() -> None:
    temp_dir, original_factory = _setup_temp_api("sync-idle")
    try:
        client = TestClient(app)
        assert client.put("/account/api-key", json={"api_key": "12345678-abcdef-secret-key"}).status_code == 200
        response = client.post("/api/v1/account/sync/drain-one")
        assert response.json() == {"status": "idle"}
    finally:
        _teardown_temp_api(temp_dir, original_factory)


def _setup_temp_api(name: str, gateway_factory=AccountSyncGateway):
    temp_dir = Path(".test_tmp") / f"{name}-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    configure_database(f"sqlite:///{temp_dir / 'account.db'}")
    state.reset_cached_graph()
    original_factory = account_sync_route.gateway_factory
    account_sync_route.gateway_factory = gateway_factory
    return temp_dir, original_factory


def _teardown_temp_api(temp_dir: Path, original_factory) -> None:
    account_sync_route.gateway_factory = original_factory
    close_database()
    state.reset_cached_graph()
    shutil.rmtree(temp_dir, ignore_errors=True)
