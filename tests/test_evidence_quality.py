from datetime import datetime, timedelta, timezone

from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.inference.action_generator import generate_actions
from gw2radar.inference.evidence_quality import evaluate_evidence_quality
from gw2radar.reports.markdown_report import generate_markdown_report


def test_mock_evidence_is_high_confidence_by_default() -> None:
    graph = build_mock_graph()
    summary = evaluate_evidence_quality(graph, list(graph.evidence.keys()))

    assert summary.confidence_label == "high"
    assert summary.has_stale is False
    assert summary.has_low_confidence is False


def test_low_confidence_evidence_downgrades_actions() -> None:
    graph = build_mock_graph()
    evidence = graph.evidence["mock:evidence:mvp_0_1"]
    evidence.confidence = 0.4

    actions = generate_actions(graph, "gw2:goal:aurora")

    assert actions
    assert all(action.urgency == "low" for action in actions)
    assert all(action.priority_score <= 0.55 for action in actions)
    assert all("low_confidence_evidence" in action.reason_codes for action in actions)
    assert all(action.constraints["evidence_confidence"] == "low" for action in actions)


def test_stale_evidence_is_marked_in_report() -> None:
    graph = build_mock_graph()
    evidence = graph.evidence["mock:evidence:mvp_0_1"]
    evidence.source_type = "gw2_api"
    evidence.fetched_at = datetime.now(timezone.utc) - timedelta(days=30)

    report = generate_markdown_report(graph, "gw2:goal:aurora")

    assert "Stale evidence present: true" in report
    assert "Evidence quality is high; verify before acting." in report
