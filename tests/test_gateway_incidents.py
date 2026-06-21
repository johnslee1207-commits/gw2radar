import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.api.routes import account_sync as account_sync_route
from gw2radar.api.routes import market as market_route
from gw2radar.api.routes import public_refresh as public_refresh_route
from gw2radar.db.session import close_database, configure_database
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import GatewayResult
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.schemas import Entity, PlayerState


class AccountSyncGateway:
    def _fetch_tokeninfo(self, api_key, *, request_id):
        return {
            "name": "Unit Test",
            "permissions": ["account", "characters", "wallet", "inventories", "progression", "tradingpost"],
        }


class DelayedPublicRefreshGateway:
    def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.RATE_LIMITED_RETRYING,
            endpoint=endpoint,
            request_id="timeline:public:rate-limit",
            retry_after_seconds=30,
            diagnostics={"params_hash": "safe-public-hash"},
        )


class DelayedMarketPriceGateway:
    def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.RATE_LIMITED_RETRYING,
            endpoint=endpoint,
            request_id="timeline:market:rate-limit",
            retry_after_seconds=30,
            diagnostics={"params_hash": "safe-market-hash"},
        )


def test_player_gateway_incident_timeline_correlates_refresh_events_without_secrets() -> None:
    temp_dir = Path(".test_tmp") / f"gateway-incidents-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    original_account_factory = account_sync_route.gateway_factory
    original_public_factory = public_refresh_route.gateway_factory
    original_market_factory = market_route.gateway_factory
    try:
        configure_database(f"sqlite:///{temp_dir / 'timeline.db'}")
        state.reset_cached_graph()
        account_sync_route.gateway_factory = AccountSyncGateway
        public_refresh_route.gateway_factory = lambda: DelayedPublicRefreshGateway()
        market_route.gateway_factory = lambda: DelayedMarketPriceGateway()
        client = TestClient(app)

        public_queued = client.post(
            "/api/v1/public/refresh",
            json={"endpoint": "/v2/items", "ids": [19721], "chunk_size": 1},
        )
        public_drained = client.post("/api/v1/public/refresh/drain-one")
        assert public_queued.status_code == 200
        assert public_drained.status_code == 200

        raw_key = "12345678-abcdef-secret-key"
        assert client.put("/account/api-key", json={"api_key": raw_key}).status_code == 200
        assert client.post("/api/v1/account/sync").status_code == 200

        assert client.post("/mock/load").status_code == 200
        _add_private_holding("gw2:item:19721", "Glob of Ectoplasm")
        price_refresh = client.post("/api/v1/market/snapshots/official-refresh?chunk_size=1")
        assert price_refresh.status_code == 200
        assert price_refresh.json()["data"]["official_price_refresh"]["status"] == "refresh_pending"

        response = client.get("/api/v1/player/gateway-incidents?limit=20")

        assert response.status_code == 200
        timeline = response.json()["data"]["gateway_incident_timeline"]
        assert timeline["schema_version"] == "gw2radar.gateway_incident_timeline.v1"
        assert timeline["timeline_status"] == "waiting_retry"
        assert timeline["retry_event_count"] >= 2
        sources = {event["source"] for event in timeline["events"]}
        assert {"account_sync", "public_refresh", "market_price_refresh"} <= sources
        public_event = next(event for event in timeline["events"] if event["source"] == "public_refresh")
        market_event = next(event for event in timeline["events"] if event["source"] == "market_price_refresh")
        assert public_event["retry_after_seconds"] == 30
        assert market_event["retryable"] is True
        assert any("Market price refresh" in action for action in timeline["next_actions"])
        assert "raw api keys" in timeline["boundary"].lower()
        assert raw_key not in str(timeline)
        assert "secret-key" not in str(timeline).lower()
    finally:
        account_sync_route.gateway_factory = original_account_factory
        public_refresh_route.gateway_factory = original_public_factory
        market_route.gateway_factory = original_market_factory
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)


def _add_private_holding(entity_id: str, name: str) -> None:
    graph = state.get_graph()
    graph.add_entity(
        Entity(
            id=entity_id,
            type=EntityType.ITEM,
            canonical_name=name,
            graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
        )
    )
    graph.add_player_state(
        PlayerState(
            id=f"state:timeline:{entity_id.rsplit(':', 1)[-1]}",
            account_id=graph.account_id or "mock:account:lee",
            entity_id=entity_id,
            graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
            quantity=7,
            location="materials",
        )
    )
    state.save_graph(graph)
