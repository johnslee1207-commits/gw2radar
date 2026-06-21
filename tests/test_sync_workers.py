from gw2radar.graph.graph_query import GraphData
from gw2radar.ingest.account_snapshot_sync import sync_account_snapshot
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import GatewayResult, Gw2ApiGateway
from gw2radar.ingest.public_static_refresh import refresh_public_items
from gw2radar.ontology.graph_layers import GraphLayer


class PayloadGateway(Gw2ApiGateway):
    def __init__(self, payloads):
        self.payloads = payloads

    def get(self, endpoint, *, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id=f"req:{endpoint}",
            payload=self.payloads[endpoint],
            evidence_id=f"evidence:{endpoint}",
        )

    def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id=f"req:{endpoint}",
            payload=[{"id": item_id, "name": f"Item {item_id}", "rarity": "Basic"} for item_id in ids],
            evidence_id=f"evidence:{endpoint}",
        )


def test_account_snapshot_sync_writes_private_player_state() -> None:
    graph = GraphData()
    gateway = PayloadGateway(
        {
            "/v2/account": {"name": "Test.1234", "world": 1001},
            "/v2/characters": ["Hero One"],
            "/v2/account/wallet": [{"id": 1, "value": 42}],
            "/v2/account/materials": [{"id": 19721, "count": 7}],
            "/v2/account/bank": [{"id": 19722, "count": 2}],
            "/v2/account/inventory": [],
            "/v2/account/achievements": [{"id": 999, "current": 1, "max": 1}],
            "/v2/commerce/transactions/current/buys": [],
            "/v2/commerce/transactions/current/sells": [],
        }
    )

    result = sync_account_snapshot(graph, gateway, api_key="12345678-abcdef-secret-key")

    assert result["status"] == "synced"
    assert result["updated_player_state"] == 5
    assert graph.entities["gw2:account:Test.1234"].graph_layer == GraphLayer.PRIVATE_PLAYER_STATE
    assert graph.entities["gw2:character:Hero One"].graph_layer == GraphLayer.PRIVATE_PLAYER_STATE
    assert all(state.graph_layer == GraphLayer.PRIVATE_PLAYER_STATE for state in graph.player_state)
    assert all(
        relation.graph_layer == GraphLayer.PRIVATE_PLAYER_STATE for relation in graph.relations
    )


def test_public_static_refresh_writes_public_items_only() -> None:
    graph = GraphData()
    gateway = PayloadGateway({})

    result = refresh_public_items(graph, gateway, item_ids=[1, 2])

    assert result["status"] == "synced"
    assert result["updated_entities"] == 2
    assert graph.entities["gw2:item:1"].canonical_name == "Item 1"
    assert all(entity.graph_layer == GraphLayer.PUBLIC_GAME for entity in graph.entities.values())
