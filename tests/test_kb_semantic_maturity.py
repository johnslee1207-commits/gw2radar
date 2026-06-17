from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.kb.kb_semantic_maturity import build_kb_semantic_maturity_report, render_kb_semantic_maturity_markdown


def test_kb_semantic_maturity_report_prioritizes_admin_console_after_release_readiness() -> None:
    report = build_kb_semantic_maturity_report()
    markdown = render_kb_semantic_maturity_markdown(report)

    assert report.schema_version == "gw2radar.kb_semantic_maturity.v1"
    assert report.overall_score >= 0.8
    assert report.maturity_label == "mature_mvp_semantic_spine"
    assert report.recommended_priorities[0].priority_id == "P18"
    assert "Admin Release Console Workflow" in markdown
    assert "release readiness gate" in markdown
    assert "reviewed disabled guild/creator policy rule packs" in markdown
    assert "build freshness notices" in markdown
    assert "summary-only semantic hint extraction" in markdown
    assert "batch promotion planner" in markdown
    assert "reviewed disabled returner/build/market rule packs" in markdown
    assert any(component.component_id == "patch_review_operations" for component in report.components)
    assert "Unreviewed rules cannot be enabled" in markdown


def test_kb_semantic_maturity_api_exports_markdown() -> None:
    client = TestClient(app)

    response = client.get("/api/v1/kb/semantic-maturity")
    markdown = client.get("/api/v1/kb/semantic-maturity/export")
    bad = client.get("/api/v1/kb/semantic-maturity/export?format=json")

    assert response.status_code == 200
    assert response.json()["data"]["report"]["recommended_priorities"][0]["priority_id"] == "P18"
    assert markdown.status_code == 200
    assert markdown.headers["content-type"].startswith("text/markdown")
    assert "# KB Semantic Maturity Analysis" in markdown.text
    assert bad.status_code == 400
