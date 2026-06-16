import shutil
from pathlib import Path
from uuid import uuid4

from gw2radar.kb_pdf.patch_note_summarizer import (
    build_recent_patch_summaries,
    render_patch_note_summary,
    write_patch_note_summaries,
)
from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord


def test_patch_note_summarizer_builds_recent_p2_structured_stub() -> None:
    record = _patch_record("Game Update Notes_ June 2, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf")
    archive = _patch_record(
        "Game Update Notes_ June 5, 2018 - Game Update Notes - Guild Wars 2 Forums.pdf",
        year=2018,
        priority="P3",
    )

    summaries = build_recent_patch_summaries([archive, record])

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.patch_id == "patch:2026-06-02"
    assert summary.evidence_id == "evidence:pdf:patch:2026-06-02"
    assert summary.review_status == "draft"
    assert summary.possible_build_impact == ["needs_manual_review"]
    assert "game_update" in summary.affected_systems


def test_patch_note_summary_writes_markdown_without_full_text_copy() -> None:
    temp_dir = Path(".test_tmp") / f"patch-summary-{uuid4().hex}"
    try:
        summary = build_recent_patch_summaries(
            [_patch_record("Game Update Notes_ May 12, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf")]
        )[0]

        written = write_patch_note_summaries([summary], temp_dir)
        markdown = written[0].read_text(encoding="utf-8")

        assert written[0] == temp_dir / "2026" / "2026-05-12.md"
        assert "changed_professions: []" in markdown
        assert "possible_market_impact: [`needs_manual_review`]" in markdown
        assert "This is a structured source stub" in markdown
        assert "full article copied" not in markdown.lower()
        assert len(markdown) < 2500
        assert render_patch_note_summary(summary) == markdown
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _patch_record(file_name: str, year: int = 2026, priority: str = "P2") -> PdfSourceRecord:
    date = "2026-06-02" if "June 2" in file_name else "2026-05-12"
    return PdfSourceRecord(
        pdf_id=f"pdf:patch:{date}",
        file_name=file_name,
        path=f"docs/knowledge_base/_sources/pdf/patch_notes/{year}/{file_name}",
        size_bytes=123,
        category="patch_note",
        year=year,
        priority=priority,
        status="pending",
        sha256="a" * 64,
    )
