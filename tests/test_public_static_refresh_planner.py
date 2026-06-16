from gw2radar.graph.graph_query import GraphData
from gw2radar.ingest.cache_store import InMemoryCacheStore
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_client import Gw2ApiResponse
from gw2radar.ingest.gw2_api_gateway import Gw2ApiGateway
from gw2radar.ingest.public_static_refresh import refresh_public_static
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer


class RecordingPublicClient:
    def __init__(self) -> None:
        self.calls = []

    def get(self, endpoint, *, params=None, api_key=None, request_id=None):
        self.calls.append((endpoint, dict(params or {})))
        ids = [int(item_id) for item_id in (params or {})["ids"].split(",")]
        return Gw2ApiResponse(
            endpoint=endpoint,
            params=params or {},
            payload=[{"id": item_id, "name": f"Entity {item_id}"} for item_id in ids],
            request_id=request_id,
        )


def test_public_refresh_dedupes_sorts_and_chunks_batch_ids() -> None:
    client = RecordingPublicClient()
    graph = GraphData()
    gateway = Gw2ApiGateway(client=client)

    result = refresh_public_static(
        graph,
        gateway,
        endpoint="/v2/achievements",
        ids=[5, 1, 5, 2, 4],
        chunk_size=2,
    )

    assert result["status"] == "synced"
    assert result["updated_entities"] == 4
    assert result["chunks"] == 2
    assert [call[1]["ids"] for call in client.calls] == ["1,2", "4,5"]
    assert graph.entities["gw2:achievement:1"].type is EntityType.ACHIEVEMENT
    assert all(entity.graph_layer == GraphLayer.PUBLIC_GAME for entity in graph.entities.values())


def test_public_refresh_records_sanitized_evidence_per_response() -> None:
    client = RecordingPublicClient()
    graph = GraphData()
    gateway = Gw2ApiGateway(client=client)

    result = refresh_public_static(graph, gateway, endpoint="/v2/currencies", ids=[1, 2], chunk_size=200)

    assert len(result["evidence_ids"]) == 1
    evidence = graph.evidence[result["evidence_ids"][0]]
    assert evidence.graph_layer == GraphLayer.PUBLIC_GAME
    assert evidence.source_type == "gw2_api"
    assert evidence.raw_payload["endpoint"] == "/v2/currencies"
    assert "api_key" not in str(evidence.raw_payload).lower()
    assert graph.entities["gw2:currency:1"].properties["evidence_id"] == evidence.id


def test_public_refresh_cache_prevents_duplicate_client_calls() -> None:
    client = RecordingPublicClient()
    cache = InMemoryCacheStore()
    gateway = Gw2ApiGateway(client=client, cache=cache)
    first_graph = GraphData()
    second_graph = GraphData()

    first = refresh_public_static(first_graph, gateway, endpoint="/v2/items", ids=[1, 2], chunk_size=200)
    second = refresh_public_static(second_graph, gateway, endpoint="/v2/items", ids=[2, 1], chunk_size=200)

    assert first["status"] == "synced"
    assert second["status"] == "synced"
    assert len(client.calls) == 1
    assert second_graph.entities["gw2:item:1"].graph_layer == GraphLayer.PUBLIC_GAME


def test_public_refresh_returns_gateway_status_without_private_writes() -> None:
    class PendingGateway:
        def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
            return GatewayResult(
                status=GatewayStatus.REFRESH_PENDING,
                endpoint=endpoint,
                request_id="req-pending",
                payload=None,
            )

    from gw2radar.ingest.gw2_api_gateway import GatewayResult

    graph = GraphData()
    result = refresh_public_static(graph, PendingGateway(), endpoint="/v2/items", ids=[1])

    assert result["status"] == GatewayStatus.REFRESH_PENDING.value
    assert result["updated_entities"] == 0
    assert graph.player_state == []
