import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.api.routes import account_sync as account_sync_route
from gw2radar.db.session import close_database, configure_database
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_client import Gw2ApiClientError
from gw2radar.ingest.gw2_api_gateway import GatewayResult
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer


class AccountSyncGateway:
    payloads = {
        "/v2/account": {"name": "Test.1234", "world": 1001},
        "/v2/characters": ["Hero One"],
        "/v2/characters/Hero%20One": {
            "name": "Hero One",
            "profession": "Mesmer",
            "level": 80,
            "equipment": [
                {"id": 1001, "slot": "Coat", "stats": {"id": 161}, "upgrades": [2001]},
                {"id": 1002, "slot": "WeaponA1", "stats": {"id": 161}, "upgrades": [2002]},
            ],
        },
        "/v2/items": [
            {"id": 1001, "name": "Synced Berserker Chest", "type": "Armor"},
            {"id": 1002, "name": "Synced Berserker Dagger", "type": "Weapon"},
            {"id": 2001, "name": "Superior Rune of the Scholar", "type": "UpgradeComponent", "details": {"type": "Rune"}},
            {"id": 2002, "name": "Superior Sigil of Force", "type": "UpgradeComponent", "details": {"type": "Sigil"}},
        ],
        "/v2/itemstats": [{"id": 161, "name": "Berserker"}],
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

    def get_batch(self, endpoint, ids, *, params=None, api_key=None, priority="P3"):
        wanted = set(ids)
        payload = [row for row in self.payloads[endpoint] if row["id"] in wanted]
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id=f"req:{endpoint}",
            payload=payload,
            evidence_id=f"evidence:{endpoint}",
        )


class MissingWalletScopeGateway(AccountSyncGateway):
    def _fetch_tokeninfo(self, api_key, *, request_id):
        return {"name": "Unit Test", "permissions": ["account", "characters", "inventories", "progression"]}


class TokeninfoClientErrorGateway(AccountSyncGateway):
    def _fetch_tokeninfo(self, api_key, *, request_id):
        raise Gw2ApiClientError("/v2/tokeninfo", 401, request_id)


def test_account_sync_requires_configured_key() -> None:
    temp_dir, original_factory = _setup_temp_api("sync-no-key")
    try:
        response = TestClient(app).post("/api/v1/account/sync")
        assert response.status_code == 400
        assert response.json()["ok"] is False
        assert response.json()["error"]["code"] == "bad_request"
        assert "API key is not configured" in response.json()["error"]["message"]
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
        assert len(response.json()["endpoint_progress"]) == 6
        assert {item["status"] for item in response.json()["endpoint_progress"]} == {"queued"}
        assert raw_key not in str(response.json())
        assert status.json()["counts"]["queued"] == 1
        assert len(status.json()["endpoint_progress"]) == 6
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
        assert response.json()["ok"] is False
        assert "wallet" in response.json()["error"]["message"]
    finally:
        _teardown_temp_api(temp_dir, original_factory)


def test_account_sync_tokeninfo_client_error_returns_reviewable_400() -> None:
    temp_dir, original_factory = _setup_temp_api("sync-tokeninfo-error", gateway_factory=TokeninfoClientErrorGateway)
    raw_key = "12345678-abcdef-secret-key"
    try:
        client = TestClient(app)
        assert client.put("/account/api-key", json={"api_key": raw_key}).status_code == 200
        response = client.post("/api/v1/account/sync")

        assert response.status_code == 400
        assert response.json()["ok"] is False
        assert "status_code=401" in response.json()["error"]["message"]
        assert raw_key not in str(response.json())
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
        assert {item["status"] for item in drained.json()["endpoint_progress"]} == {"succeeded"}
        assert status.json()["counts"]["succeeded"] == 1
        assert {item["status"] for item in status.json()["endpoint_progress"]} == {"succeeded"}

        state.reset_cached_graph()
        graph = state.get_graph()
        assert graph.entities["gw2:account:Test.1234"].graph_layer == GraphLayer.PRIVATE_PLAYER_STATE
        assert graph.entities["gw2:character:Hero One"].type == EntityType.CHARACTER
        assert graph.entities["gw2:character:Hero One"].graph_layer == GraphLayer.PRIVATE_PLAYER_STATE
        assert graph.entities["gw2:character:Hero One"].properties["profession"] == "Mesmer"
        equipment = graph.entities["gw2:character:Hero One"].properties["equipment"]
        assert equipment
        assert equipment[0]["item_name"] == "Synced Berserker Chest"
        assert equipment[0]["stat_combo"] == "Berserker"
        assert equipment[0]["metadata_sources"] == ["official_items", "official_itemstats"]
        assert any(item["equipment_category"] == "rune" for item in equipment)
        assert any(item["equipment_category"] == "sigil" for item in equipment)
        assert graph.entities["gw2:item:1001"].canonical_name == "Synced Berserker Chest"
        assert graph.entities["gw2:item:1001"].properties["stat_combo"] == "Berserker"
        assert graph.entities["gw2:item:2001"].properties["equipment_category"] == "rune"
        assert graph.entities["gw2:item:2002"].properties["equipment_category"] == "sigil"
        assert all(player_state.graph_layer == GraphLayer.PRIVATE_PLAYER_STATE for player_state in graph.player_state)
        assert all(
            relation.graph_layer == GraphLayer.PRIVATE_PLAYER_STATE
            for relation in graph.relations
            if relation.subject_id == "gw2:account:Test.1234"
        )

        snapshots = client.get("/api/v1/builds/character-snapshots")
        assert snapshots.status_code == 200
        assert snapshots.json()["data"]["snapshots"][0]["source"] == "synced_official_api"
        assert snapshots.json()["data"]["snapshots"][0]["character_name"] == "Hero One"
        snapshot_id = snapshots.json()["data"]["snapshots"][0]["snapshot_id"]
        account_gear = client.get(f"/api/v1/builds/character-snapshots/{snapshot_id}/account-gear")
        assert account_gear.status_code == 200
        assert account_gear.json()["data"]["account_gear"]["gear"][0]["item_name"] == "Synced Berserker Chest"
        assert account_gear.json()["data"]["account_gear"]["gear"][0]["stat_combo"] == "Berserker"
        categories = {item["equipment_category"] for item in account_gear.json()["data"]["account_gear"]["gear"]}
        assert {"armor", "weapon", "rune", "sigil"} <= categories
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
