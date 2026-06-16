import csv
import shutil
from io import StringIO
from pathlib import Path
from uuid import uuid4

from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_repository import list_rules
from gw2radar.kb.patch_dashboard_export import (
    PATCH_DASHBOARD_CSV_FIELDS,
    render_patch_dashboard_csv,
    render_patch_dashboard_markdown,
)
from gw2radar.kb.patch_impact_review import (
    PatchImpactReviewInput,
    build_patch_review_dashboard,
    persist_patch_rule_candidates,
    save_patch_impact_review,
)
from gw2radar.kb_pdf.patch_note_summarizer import build_recent_patch_summaries, write_patch_note_summaries
from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord


def test_patch_dashboard_export_renders_deterministic_markdown_and_csv(monkeypatch) -> None:
    temp_dir = Path(".test_tmp") / f"patch-dashboard-export-{uuid4().hex}"
    try:
        monkeypatch.setenv("GW2RADAR_PATCH_RULE_AUDIT_STORE", str(temp_dir / "audit.jsonl"))
        summary_root = temp_dir / "patch_notes"
        review_store = temp_dir / "reviews.jsonl"
        write_patch_note_summaries(
            [
                build_recent_patch_summaries(
                    [_patch_record("Game Update Notes_ June 2, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf")]
                )[0]
            ],
            summary_root,
        )
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            save_patch_impact_review(
                PatchImpactReviewInput(
                    patch_id="patch:2026-06-02",
                    affected_systems=["build", "market"],
                    build_impact=["Review build assumptions."],
                    market_impact=["Watch prices."],
                    reviewer="export-reviewer",
                ),
                summary_root,
                review_store,
            )
            persist_patch_rule_candidates(session, "patch:2026-06-02", True, summary_root, review_store)
            items = build_patch_review_dashboard(list_rules(session), summary_root, review_store)

        markdown = render_patch_dashboard_markdown(items)
        csv_text = render_patch_dashboard_csv(items)
        rows = list(csv.DictReader(StringIO(csv_text)))

        assert markdown.startswith("# Patch Review Dashboard")
        assert "| 2026-06-02 | patch:2026-06-02 | persisted | reviewed | 2 | 3 | export-reviewer |" in markdown
        assert "Boundary: review queue export only" in markdown
        assert "Review build assumptions." in markdown
        assert PATCH_DASHBOARD_CSV_FIELDS == list(rows[0].keys())
        assert rows[0]["patch_id"] == "patch:2026-06-02"
        assert rows[0]["lifecycle_status"] == "persisted"
        assert rows[0]["audit_action_counts"] == "persist:2;review:1"
        assert "full article copied" not in markdown.lower()
        assert "full article copied" not in csv_text.lower()
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)


def _patch_record(file_name: str) -> PdfSourceRecord:
    return PdfSourceRecord(
        pdf_id="pdf:patch:2026-06-02",
        file_name=file_name,
        path=f"docs/knowledge_base/_sources/pdf/patch_notes/2026/{file_name}",
        size_bytes=123,
        category="patch_note",
        year=2026,
        priority="P2",
        status="pending",
        sha256="a" * 64,
    )
