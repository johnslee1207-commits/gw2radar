import shutil
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.api.routes import market as market_route
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.models import MarketSnapshotModel
from gw2radar.db.session import close_database, configure_database
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import GatewayResult
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.schemas import Entity, PlayerState


class OfficialPriceGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[int]]] = []

    def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
        self.calls.append((endpoint, [int(item_id) for item_id in ids]))
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id=f"price:{len(self.calls)}",
            payload=[
                {
                    "id": int(item_id),
                    "buys": {"unit_price": 12000 + int(item_id), "quantity": 100},
                    "sells": {"unit_price": 12500 + int(item_id), "quantity": 200},
                }
                for item_id in ids
            ],
            evidence_id=f"evidence:price:{len(self.calls)}",
        )


def test_official_price_refresh_records_public_snapshots_for_account_holdings() -> None:
    temp_dir = Path(".test_tmp") / f"official-price-refresh-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    original_factory = market_route.gateway_factory
    gateway = OfficialPriceGateway()
    try:
        configure_database(f"sqlite:///{temp_dir / 'market.db'}")
        init_db()
        state.reset_cached_graph()
        market_route.gateway_factory = lambda: gateway
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200
        graph = state.get_graph()
        graph.add_entity(
            Entity(
                id="gw2:item:19721",
                type=EntityType.ITEM,
                canonical_name="Glob of Ectoplasm",
                graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
            )
        )
        graph.add_player_state(
            PlayerState(
                id="state:official-price:19721",
                account_id=graph.account_id or "mock:account:lee",
                entity_id="gw2:item:19721",
                graph_layer=GraphLayer.PRIVATE_PLAYER_STATE,
                quantity=7,
                location="materials",
            )
        )
        state.save_graph(graph)

        response = client.post("/api/v1/market/snapshots/official-refresh?chunk_size=2")
        value = client.get("/api/v1/player/account-value")

        assert response.status_code == 200
        refresh = response.json()["data"]["official_price_refresh"]
        assert refresh["status"] == "succeeded"
        assert refresh["requested_item_count"] >= 1
        assert refresh["refreshed_item_count"] >= 1
        assert all(call[0] == "/v2/commerce/prices" for call in gateway.calls)
        assert value.json()["data"]["account_value_snapshot"]["summary"]["total_value_buy_copper"] > 0
        with db_session.SessionLocal() as session:
            sources = {row.source for row in session.query(MarketSnapshotModel).all()}
        assert sources == {"official_commerce_api"}
    finally:
        market_route.gateway_factory = original_factory
        close_database()
        state.reset_cached_graph()
        shutil.rmtree(temp_dir, ignore_errors=True)
