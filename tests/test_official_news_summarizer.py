import shutil
from pathlib import Path
from uuid import uuid4

from gw2radar.kb_pdf.official_news_summarizer import (
    build_official_news_summaries,
    render_official_news_summary,
    write_official_news_summaries,
)
from gw2radar.kb_pdf.pdf_evidence_writer import build_evidence_records
from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord


def test_official_news_summarizer_builds_source_stub() -> None:
    record = _news_record("The Future of the Guild Wars Franchise_ Our Commitment to Tyria – GuildWars2.com.pdf")
    ignored = _patch_record()

    summaries = build_official_news_summaries([ignored, record])
    evidence = build_evidence_records([record])[0]

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.news_id.startswith("news:official_news:")
    assert summary.evidence_id.startswith("evidence:pdf:official_news:")
    assert summary.review_status == "draft"
    assert "official_news" in summary.affected_systems
    assert evidence.confidence == 0.9


def test_official_news_summary_writes_markdown_without_full_text_copy() -> None:
    temp_dir = Path(".test_tmp") / f"official-news-{uuid4().hex}"
    try:
        summary = build_official_news_summaries(
            [_news_record("New Raid Encounter, Quickplay, and Raid System Improvements – GuildWars2.com.pdf")]
        )[0]

        written = write_official_news_summaries([summary], temp_dir)
        markdown = written[0].read_text(encoding="utf-8")

        assert written[0].name == "new_raid_encounter_quickplay_and_raid_system_improvements.md"
        assert "affected_systems: [`official_news`, `group_content`]" in markdown
        assert "possible_product_context: [`needs_manual_review`]" in markdown
        assert "full official news text" in markdown
        assert "full article copied" not in markdown.lower()
        assert len(markdown) < 2500
        assert render_official_news_summary(summary) == markdown
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _news_record(file_name: str) -> PdfSourceRecord:
    return PdfSourceRecord(
        pdf_id="pdf:official_news:the_future_of_the_guild_wars_franchise",
        file_name=file_name,
        path=f"docs/knowledge_base/_sources/pdf/news/{file_name}",
        size_bytes=123,
        category="official_news",
        year=None,
        priority="P2",
        status="pending",
        sha256="a" * 64,
    )


def _patch_record() -> PdfSourceRecord:
    return PdfSourceRecord(
        pdf_id="pdf:patch:2026-06-02",
        file_name="Game Update Notes_ June 2, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf",
        path="docs/knowledge_base/_sources/pdf/patch_notes/2026/Game Update Notes_ June 2, 2026.pdf",
        size_bytes=123,
        category="patch_note",
        year=2026,
        priority="P2",
        status="pending",
        sha256="b" * 64,
    )
