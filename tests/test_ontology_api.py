from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app


def test_ontology_enrich_endpoint() -> None:
    state.reset_cached_graph()
    client = TestClient(app)
    assert client.post("/mock/load").status_code == 200
    resp = client.post("/api/v1/ontology/enrich")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "enriched"
    assert data["entity_count"] > 0


def test_impact_sell_item_reserved() -> None:
    state.reset_cached_graph()
    client = TestClient(app)
    client.post("/mock/load")
    resp = client.post("/api/v1/ontology/impact/sell-item?item_id=gw2:item:mystic_coin")
    assert resp.status_code == 200
    impact = resp.json()["data"]["impact"]
    assert impact["risk"] == "high"
    assert len(impact["affected_goals"]) > 0
    assert len(impact["warnings"]) > 0


def test_impact_goal_change() -> None:
    state.reset_cached_graph()
    client = TestClient(app)
    client.post("/mock/load")
    resp = client.post("/api/v1/ontology/impact/goal-change?goal_id=gw2:goal:aurora")
    assert resp.status_code == 200
    impact = resp.json()["data"]["impact"]
    assert impact["target"] == "gw2:goal:aurora"


def test_impact_goal_not_found() -> None:
    state.reset_cached_graph()
    client = TestClient(app)
    client.post("/mock/load")
    resp = client.post("/api/v1/ontology/impact/goal-change?goal_id=nonexistent")
    assert resp.status_code == 404


def test_impact_build_stale() -> None:
    state.reset_cached_graph()
    client = TestClient(app)
    client.post("/mock/load")
    resp = client.post("/api/v1/ontology/impact/build-stale?build_id=nonexistent")
    assert resp.status_code == 200
    assert "not found" in resp.json()["data"]["impact"]["warnings"][0]


def test_ontology_registry() -> None:
    state.reset_cached_graph()
    client = TestClient(app)
    resp = client.get("/api/v1/ontology/registry")
    assert resp.status_code == 200
    registry = resp.json()["data"]["registry"]
    assert "reserve_material_for_goal" in registry
    assert "generate_do_not_sell" in registry
    assert "generate_legendary_plan" in registry


def test_ontology_qa_endpoint() -> None:
    state.reset_cached_graph()
    client = TestClient(app)
    client.post("/mock/load")
    resp = client.post("/api/v1/ontology/qa")
    assert resp.status_code == 200
    qa = resp.json()["data"]["qa"]
    assert "passed" in qa
    assert "summary" in qa
    assert len(qa["checks"]) > 0


def test_query_relations() -> None:
    state.reset_cached_graph()
    client = TestClient(app)
    client.post("/mock/load")
    resp = client.post("/api/v1/ontology/query/relations?predicate=requires")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["count"] > 0
    for rel in data["relations"]:
        assert rel["predicate"] == "requires"


def test_ontology_enrich_adds_governance_to_all_entities() -> None:
    state.reset_cached_graph()
    client = TestClient(app)
    client.post("/mock/load")
    enrich = client.post("/api/v1/ontology/enrich")
    assert enrich.status_code == 200
    qa = client.post("/api/v1/ontology/qa")
    assert qa.status_code == 200
    checks = qa.json()["data"]["qa"]["checks"]
    entity_check = next((c for c in checks if c["name"] == "evidence_refs_exist"), None)
    assert entity_check is not None
