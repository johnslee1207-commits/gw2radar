from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.commercial.returner_readiness import (
    build_returner_readiness_report,
    render_returner_readiness_markdown,
)
from gw2radar.graph.graph_builder import build_mock_graph


client = TestClient(app)


def test_returner_readiness_scores_required_dimensions_without_inventing_facts() -> None:
    report = build_returner_readiness_report(build_mock_graph())

    dimensions = {dimension.dimension_id: dimension for dimension in report.dimensions}

    assert report.schema_version == "gw2radar.returner_readiness.v1"
    assert report.overall_score > 0
    assert set(dimensions) == {"travel", "combat", "progression", "legendary", "group_pve"}
    assert dimensions["travel"].assumptions
    assert dimensions["combat"].blockers
    assert "No automatic trading" in " ".join(report.safety_boundaries)
    assert report.what_to_do_first


def test_returner_readiness_api_and_markdown_export() -> None:
    response = client.get("/api/v1/returner/readiness")
    markdown = client.get("/api/v1/returner/readiness/export")
    bad_format = client.get("/api/v1/returner/readiness/export?format=json")

    assert response.status_code == 200
    readiness = response.json()["data"]["readiness"]
    assert readiness["schema_version"] == "gw2radar.returner_readiness.v1"
    assert readiness["overall_status"] in {"ready", "recoverable", "needs_review"}
    assert len(readiness["dimensions"]) == 5
    assert markdown.status_code == 200
    assert "# Returner Readiness Report" in markdown.text
    assert bad_format.status_code == 400


def test_returner_readiness_markdown_preserves_boundaries() -> None:
    report = build_returner_readiness_report(build_mock_graph())
    markdown = render_returner_readiness_markdown(report)

    assert "## Readiness Scores" in markdown
    assert "No gameplay automation is performed." in markdown
    assert "Assumption:" in markdown
