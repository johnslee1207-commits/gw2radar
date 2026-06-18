from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.report_engine import generate_report_preview
from gw2radar.graph.graph_builder import build_mock_graph


def test_free_report_preview_hides_paid_only_detail() -> None:
    output_root = Path(".test_tmp") / f"report-preview-{uuid4().hex}"
    graph = build_mock_graph()

    preview = generate_report_preview(graph, "gw2:goal:aurora", output_root=output_root)
    preview_text = str(preview["preview"])

    assert "GW2Radar Free Report Preview" in preview_text
    assert "Top Recommendations" in preview_text
    assert "Data Freshness & Source Confidence" in preview_text
    assert "Missing Requirements" not in preview_text
    assert "Full missing-material tables" in preview_text
    assert Path(str(preview["manifest_path"])).exists()
