from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.reports.markdown_report import generate_markdown_report


def test_markdown_report_contains_required_sections() -> None:
    graph = build_mock_graph()
    report = generate_markdown_report(graph, "gw2:goal:aurora")

    assert "## Active Goal" in report
    assert "## Missing Requirements" in report
    assert "## Recommended Actions Today" in report
    assert "## Evidence Notes" in report
    assert "Evidence confidence: high" in report
    assert "Aurora" in report
