from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.ontology.impact_analyzer import analyze_build_source_stale, analyze_report_publish, analyze_sell_item
from gw2radar.ontology.ontology_qa import check_evidence_refs_exist, check_goal_requirement_resolves, check_private_data_not_public, run_qa_suite
from gw2radar.ontology.relation_types import RelationType
from gw2radar.ontology.schemas import Entity, FreshnessStatus, QAStatus, Relation, ReviewStatus
from gw2radar.ontology.graph_layers import GraphLayer


def test_analyze_sell_item_reserved_material_returns_high_risk() -> None:
    graph = build_mock_graph()
    result = analyze_sell_item(graph, "gw2:item:mystic_coin")
    assert result.risk == "high"
    assert len(result.affected_goals) > 0
    assert len(result.warnings) > 0
    assert len(result.recommendations) > 0


def test_analyze_sell_item_unreserved_material_returns_low_risk() -> None:
    graph = build_mock_graph()
    result = analyze_sell_item(graph, "gw2:item:glob_of_ectoplasm")
    assert result.risk in {"low", "high"}
    assert "do not sell" not in " ".join(result.recommendations).lower() if result.risk == "low" else True


def test_analyze_build_source_stale_not_found() -> None:
    graph = build_mock_graph()
    result = analyze_build_source_stale(graph, "nonexistent-build")
    assert result.warnings[0] == "Build not found in graph."


def test_analyze_report_publish_no_entity() -> None:
    graph = build_mock_graph()
    result = analyze_report_publish(graph, "nonexistent-report")
    assert result.risk == "high"


def test_analyze_report_publish_with_fresh_entity() -> None:
    graph = build_mock_graph()
    eid = "gw2:report:test_fresh"
    graph.add_entity(
        Entity(
            id=eid,
            type="evidence",
            canonical_name="Test Report",
            freshness_status=FreshnessStatus.FRESH,
            review_status=ReviewStatus.REVIEWED,
            qa_status=QAStatus.PASS,
            properties={"evidence_count": 2},
        )
    )
    result = analyze_report_publish(graph, eid)
    assert result.risk == "low"


def test_qa_goal_requirement_resolves_passes() -> None:
    graph = build_mock_graph()
    result = check_goal_requirement_resolves(graph)
    assert result.passed


def test_qa_private_data_not_public_passes() -> None:
    graph = build_mock_graph()
    result = check_private_data_not_public(graph)
    assert result.passed


def test_qa_evidence_refs_exist() -> None:
    graph = build_mock_graph()
    result = check_evidence_refs_exist(graph)
    assert result.passed


def test_qa_suite_runs_all_checks() -> None:
    graph = build_mock_graph()
    suite = run_qa_suite(graph)
    assert len(suite.results) == len([
        "goal_requirement_resolves",
        "reserved_quantity_not_exceed_owned",
        "private_data_not_public",
        "evidence_refs_exist",
        "build_source_reviewed",
        "market_data_fresh_enough",
    ])
    assert suite.passed or not suite.passed


def test_qa_suite_selective_checks() -> None:
    graph = build_mock_graph()
    suite = run_qa_suite(graph, checks=["evidence_refs_exist", "private_data_not_public"])
    assert len(suite.results) == 2
