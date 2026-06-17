from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.kb.kb_source_semantics import (
    build_source_semantic_report,
    extract_source_semantic_hint,
    render_source_semantic_report_csv,
    render_source_semantic_report_markdown,
)


def test_source_semantic_extraction_reads_summary_only_markdown() -> None:
    temp_dir = Path(".test_tmp") / f"source-semantics-{uuid4().hex}"
    source = temp_dir / "patch_notes" / "2026" / "2026-06-02.md"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(_patch_note_markdown(), encoding="utf-8")

    hint = extract_source_semantic_hint(source, temp_dir)

    assert hint.source_path == "patch_notes/2026/2026-06-02.md"
    assert hint.source_kind == "patch_note_summary"
    assert hint.evidence_refs == ["evidence:pdf:patch:2026-06-02"]
    assert "gw2:system:patch_notes" in hint.ontology_links
    assert "gw2:system:game_update" in hint.ontology_links
    assert "review_build_freshness" in hint.action_hints
    assert "review_market_watchlist" in hint.action_hints
    assert hint.blockers == []


def test_source_semantic_report_exports_markdown_and_csv() -> None:
    temp_dir = Path(".test_tmp") / f"source-semantics-report-{uuid4().hex}"
    (temp_dir / "official").mkdir(parents=True, exist_ok=True)
    (temp_dir / "official" / "api_rate_limit.md").write_text(_official_api_markdown(), encoding="utf-8")
    (temp_dir / "news" / "official").mkdir(parents=True, exist_ok=True)
    (temp_dir / "news" / "official" / "raid_news.md").write_text(_official_news_markdown(), encoding="utf-8")

    report = build_source_semantic_report(temp_dir)
    markdown = render_source_semantic_report_markdown(report)
    csv_text = render_source_semantic_report_csv(report)

    assert report.schema_version == "gw2radar.kb_source_semantics.v1"
    assert report.hint_count == 2
    assert report.blocker_count == 0
    assert report.source_kind_counts["official_source_summary"] == 1
    assert report.source_kind_counts["official_news_summary"] == 1
    assert "Official Source Semantic Extraction" in markdown
    assert "source_path,source_kind,ontology_links,action_hints,evidence_refs,blockers" in csv_text
    assert "full article copied" not in markdown.lower()


def test_source_semantics_api_exports_json_markdown_and_csv() -> None:
    temp_dir = Path(".test_tmp") / f"source-semantics-api-{uuid4().hex}"
    (temp_dir / "patch_notes" / "2026").mkdir(parents=True, exist_ok=True)
    (temp_dir / "patch_notes" / "2026" / "2026-06-02.md").write_text(_patch_note_markdown(), encoding="utf-8")
    client = TestClient(app)

    response = client.get("/api/v1/kb/source-semantics", params={"source_root": str(temp_dir)})
    markdown = client.get("/api/v1/kb/source-semantics/export", params={"source_root": str(temp_dir)})
    csv_response = client.get(
        "/api/v1/kb/source-semantics/export",
        params={"source_root": str(temp_dir), "format": "csv"},
    )
    bad = client.get("/api/v1/kb/source-semantics/export", params={"source_root": str(temp_dir), "format": "json"})

    assert response.status_code == 200
    assert response.json()["data"]["report"]["hint_count"] == 1
    assert markdown.status_code == 200
    assert markdown.headers["content-type"].startswith("text/markdown")
    assert csv_response.status_code == 200
    assert csv_response.headers["content-type"].startswith("text/csv")
    assert bad.status_code == 400


def _patch_note_markdown() -> str:
    return """---
title: GW2 Patch Note 2026-06-02
domain: official
content_type: summary
summary: Structured draft summary for an official GW2 patch note; impact fields require manual review.
source_refs:
linked_entities: gw2:system:patch_notes
linked_actions: INGEST_SOURCE
confidence: 0.65
review_status: draft
---

# GW2 Patch Note 2026-06-02

- evidence_id: `evidence:pdf:patch:2026-06-02`

## Structured Impact Fields

- affected_systems: [`patch_notes`, `game_update`]
- possible_build_impact: [`needs_manual_review`]
- possible_market_impact: [`needs_manual_review`]

## Review Boundary

- This is a structured source stub generated from the downloaded PDF inventory.
- It does not copy full patch-note text.
"""


def _official_api_markdown() -> str:
    return """---
title: GW2 API rate limit and best-practice summary
domain: official
content_type: source_note
summary: Source-linked summary derived from official API evidence; avoid copying full source text.
linked_entities: gw2:system:official_api
linked_actions: REFRESH_PUBLIC_STATIC_DATA
source_refs:
confidence: 0.95
review_status: draft
---

# GW2 API rate limit and best-practice summary

- Evidence ID: `evidence:pdf:api:best_practices`
- Processing note: this article is a concise source summary, not a full-text copy of the PDF.
"""


def _official_news_markdown() -> str:
    return """---
title: New Raid Encounter And Raid System Improvements
domain: official
content_type: summary
summary: Structured draft source note for official Guild Wars 2 news; use source evidence for verification.
source_refs:
linked_entities: gw2:system:official_news
linked_actions: INGEST_SOURCE
confidence: 0.75
review_status: draft
---

# New Raid Encounter And Raid System Improvements

- evidence_id: `evidence:pdf:official_news:raid`

## Structured News Fields

- affected_systems: [`official_news`, `group_content`]
- possible_product_context: [`needs_manual_review`]
"""
