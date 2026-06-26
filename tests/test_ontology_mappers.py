from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.ontology.entity_types import EntityType
from gw2radar.ontology.graph_layers import GraphLayer
from gw2radar.ontology.mappers import (
    enrich_account_entities,
    enrich_evidence_entities,
    enrich_goal_entities,
    enrich_report_entities,
)
from gw2radar.ontology.schemas import FreshnessStatus


def test_account_mapper_enriches_private_entities() -> None:
    graph = build_mock_graph()
    enrich_account_entities(graph)
    for eid, entity in graph.entities.items():
        if entity.graph_layer == GraphLayer.PRIVATE_PLAYER_STATE:
            assert entity.freshness_status is not None
            assert len(entity.source_refs) >= 1
            assert entity.source_refs[0].privacy_scope == "private_summary_only"


def test_account_mapper_sets_holding_count() -> None:
    graph = build_mock_graph()
    enrich_account_entities(graph)
    accounts = [e for e in graph.entities.values() if e.type == EntityType.ACCOUNT]
    for acc in accounts:
        assert "holding_count" in acc.properties
        assert acc.properties["holding_count"] > 0


def test_goal_mapper_sets_requirement_count() -> None:
    graph = build_mock_graph()
    enrich_goal_entities(graph)
    goals = [e for e in graph.entities.values() if e.type == EntityType.GOAL]
    for goal in goals:
        assert "requirement_count" in goal.properties
        assert goal.properties["requirement_count"] > 0
        assert len(goal.source_refs) >= 1


def test_evidence_mapper_creates_evidence_entities() -> None:
    graph = build_mock_graph()
    enrich_evidence_entities(graph)
    evidence_entities = [e for e in graph.entities.values() if e.type == EntityType.EVIDENCE]
    assert len(evidence_entities) >= 1
    for ee in evidence_entities:
        assert ee.freshness_status is not None
        assert len(ee.source_refs) >= 1


def test_report_mapper_creates_report_entity() -> None:
    graph = build_mock_graph()
    enrich_report_entities(graph, report_id="test-report-001", report_type="legendary_plan", evidence_ids=["mock:evidence:mvp_0_1"])
    report_entities = [e for e in graph.entities.values() if "Report:" in (e.canonical_name or "")]
    assert len(report_entities) >= 1
    report = report_entities[0]
    assert report.properties["report_type"] == "legendary_plan"
    assert report.properties["evidence_count"] == 1


def test_all_mappers_together() -> None:
    graph = build_mock_graph()
    enrich_account_entities(graph)
    enrich_goal_entities(graph)
    enrich_evidence_entities(graph)
    enrich_report_entities(graph, report_id="test-report-002", report_type="build_fit")
    for eid, entity in graph.entities.items():
        assert entity.freshness_status is not None
        assert entity.review_status is not None
        assert entity.qa_status is not None
    evidence_ents = [e for e in graph.entities.values() if e.type == EntityType.EVIDENCE]
    assert len(evidence_ents) >= 1
    report_ents = [e for e in graph.entities.values() if "Report:" in (e.canonical_name or "")]
    assert len(report_ents) >= 1
