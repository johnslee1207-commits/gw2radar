from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_domain_rule_packs import list_domain_rule_packs
from gw2radar.kb.kb_promotion_planner import build_kb_promotion_plan
from gw2radar.kb.kb_release_readiness import (
    build_kb_release_readiness_report,
    render_kb_release_readiness_csv,
    render_kb_release_readiness_markdown,
)
from gw2radar.kb.kb_semantic_maturity import build_kb_semantic_maturity_report
from gw2radar.kb.kb_source_semantics import build_source_semantic_report


def test_kb_release_readiness_builds_operator_checklist() -> None:
    temp_dir = Path(".test_tmp") / f"kb-release-readiness-{uuid4().hex}"
    _write_source_stub(temp_dir)

    semantic = build_kb_semantic_maturity_report()
    source_semantics = build_source_semantic_report(temp_dir)
    promotion = build_kb_promotion_plan([], state.get_graph(), include_rule_packs=True)
    report = build_kb_release_readiness_report(
        semantic,
        promotion,
        source_semantics,
        [],
        [],
        list_domain_rule_packs(),
    )
    markdown = render_kb_release_readiness_markdown(report)
    csv_text = render_kb_release_readiness_csv(report)

    assert report.schema_version == "gw2radar.kb_release_readiness.v1"
    assert report.ready_for_release is True
    assert any(item.check_id == "reviewed_rule_packs" for item in report.checklist)
    assert any("import selected reviewed rule packs" in step.lower() for step in report.next_operator_steps)
    assert "# KB Release Readiness And Operating Playbook" in markdown
    assert "This playbook is read-only" in markdown
    assert "check_id,title,status,summary,evidence_refs,operator_steps" in csv_text


def test_kb_release_readiness_api_exports_json_markdown_and_csv() -> None:
    temp_dir = Path(".test_tmp") / f"kb-release-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        state.reset_cached_graph()
        client = TestClient(app)
        assert client.post("/mock/load").status_code == 200

        response = client.get("/api/v1/kb/release-readiness")
        markdown = client.get("/api/v1/kb/release-readiness/export")
        csv_response = client.get("/api/v1/kb/release-readiness/export?format=csv")
        bad = client.get("/api/v1/kb/release-readiness/export?format=json")

        assert response.status_code == 200
        payload = response.json()["data"]["report"]
        assert payload["schema_version"] == "gw2radar.kb_release_readiness.v1"
        assert len(payload["checklist"]) >= 6
        assert any(item["check_id"] == "acquisition_readiness" for item in payload["checklist"])
        assert markdown.status_code == 200
        assert markdown.headers["content-type"].startswith("text/markdown")
        assert "KB Release Readiness" in markdown.text
        assert "Acquisition source and job readiness" in markdown.text
        assert csv_response.status_code == 200
        assert csv_response.headers["content-type"].startswith("text/csv")
        assert "acquisition_readiness" in csv_response.text
        assert bad.status_code == 400
    finally:
        close_database()
        state.reset_cached_graph()


def _write_source_stub(root: Path) -> None:
    path = root / "official" / "api_summary.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """---
title: GW2 API summary
domain: official
content_type: source_note
summary: Source-linked summary derived from official API evidence.
linked_entities: gw2:system:official_api
linked_actions: REFRESH_PUBLIC_STATIC_DATA
source_refs:
confidence: 0.95
review_status: draft
---

# GW2 API summary

- Evidence ID: `evidence:pdf:api:main`
- Processing note: this article is a concise source summary.
""",
        encoding="utf-8",
    )
