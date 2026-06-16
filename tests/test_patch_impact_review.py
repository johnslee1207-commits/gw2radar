import shutil
from pathlib import Path
from uuid import uuid4

import pytest

from gw2radar.kb.kb_models import KnowledgeReviewStatus
from gw2radar.kb.kb_repository import enable_rule, list_rules
from gw2radar.kb.patch_impact_review import (
    PatchImpactReviewInput,
    build_patch_rule_candidates,
    list_patch_impact_drafts,
    list_pending_patch_impact_drafts,
    persist_patch_rule_candidates,
    save_patch_impact_review,
)
from gw2radar.kb.patch_rule_audit import list_patch_rule_audit_events
from gw2radar.kb_pdf.patch_note_summarizer import build_recent_patch_summaries, write_patch_note_summaries
from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database


def test_patch_impact_review_lists_drafts_by_year_and_pending_status() -> None:
    temp_dir = Path(".test_tmp") / f"patch-review-list-{uuid4().hex}"
    try:
        summary_root = temp_dir / "patch_notes"
        review_store = temp_dir / "reviews.jsonl"
        write_patch_note_summaries(
            [
                build_recent_patch_summaries(
                    [_patch_record("Game Update Notes_ June 2, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf")]
                )[0],
                build_recent_patch_summaries(
                    [_patch_record("Game Update Notes_ May 21, 2024 - Game Update Notes - Guild Wars 2 Forums.pdf", 2024)]
                )[0],
            ],
            summary_root,
        )

        drafts_2026 = list_patch_impact_drafts(summary_root, review_store, year=2026)

        assert [draft.patch_id for draft in drafts_2026] == ["patch:2026-06-02"]
        assert drafts_2026[0].review_status == KnowledgeReviewStatus.DRAFT
        assert "game_update" in drafts_2026[0].affected_systems
        assert list_pending_patch_impact_drafts(summary_root, review_store, year=2026) == drafts_2026
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_patch_impact_review_saves_manual_impacts_and_builds_disabled_rule_candidates(monkeypatch) -> None:
    temp_dir = Path(".test_tmp") / f"patch-review-rule-{uuid4().hex}"
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

        review = save_patch_impact_review(
            PatchImpactReviewInput(
                patch_id="patch:2026-06-02",
                affected_systems=["build", "market", "game_update"],
                build_impact=["Review condition damage build assumptions."],
                market_impact=["Watch affected material prices before crafting."],
                reviewer="qa",
                notes="Source checked manually.",
            ),
            summary_root,
            review_store,
        )
        candidate = build_patch_rule_candidates("patch:2026-06-02", summary_root, review_store)
        reviewed_drafts = list_pending_patch_impact_drafts(summary_root, review_store)

        assert review.review_status == KnowledgeReviewStatus.REVIEWED
        assert reviewed_drafts == []
        assert [rule.domain.value for rule in candidate.rules] == ["build", "market"]
        assert [rule.action_type for rule in candidate.rules] == ["complete_achievement", "watch_price"]
        assert all(rule.review_status == KnowledgeReviewStatus.REVIEWED for rule in candidate.rules)
        assert all(rule.enabled is False for rule in candidate.rules)
        assert candidate.rules[0].evidence_refs[0] == "evidence:pdf:patch:2026-06-02"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_patch_impact_review_persists_candidates_disabled_until_enable_gate(monkeypatch) -> None:
    temp_dir = Path(".test_tmp") / f"patch-review-persist-{uuid4().hex}"
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
        save_patch_impact_review(
            PatchImpactReviewInput(
                patch_id="patch:2026-06-02",
                affected_systems=["build", "market"],
                build_impact=["Review build assumptions."],
                market_impact=["Watch affected prices."],
                reviewer="qa",
            ),
            summary_root,
            review_store,
        )
        configure_database(f"sqlite:///{temp_dir / 'kb.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            with pytest.raises(ValueError, match="explicit manual confirmation"):
                persist_patch_rule_candidates(session, "patch:2026-06-02", False, summary_root, review_store)

            persisted = persist_patch_rule_candidates(session, "patch:2026-06-02", True, summary_root, review_store)
            duplicate = persist_patch_rule_candidates(session, "patch:2026-06-02", True, summary_root, review_store)
            enabled = enable_rule(session, persisted.rules[0].rule_id)
            rules = list_rules(session)
        audit_events = list_patch_rule_audit_events(audit_store=temp_dir / "audit.jsonl")

        assert persisted.created_count == 2
        assert persisted.skipped_existing_count == 0
        assert all(rule.enabled is False for rule in persisted.rules)
        assert duplicate.created_count == 0
        assert duplicate.skipped_existing_count == 2
        assert enabled.enabled is True
        assert len(rules) == 2
        assert [event.action.value for event in audit_events] == ["review", "persist", "persist"]
        assert audit_events[1].rule_id == persisted.rules[0].rule_id
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_patch_impact_review_rejects_unknown_system_and_unreviewed_candidates() -> None:
    temp_dir = Path(".test_tmp") / f"patch-review-guard-{uuid4().hex}"
    try:
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

        with pytest.raises(ValueError, match="reviewed patch impact record"):
            build_patch_rule_candidates("patch:2026-06-02", summary_root, review_store)
        with pytest.raises(ValueError, match="Unsupported affected system"):
            PatchImpactReviewInput(
                patch_id="patch:2026-06-02",
                affected_systems=["unsupported"],
                build_impact=["Review builds."],
            )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _patch_record(file_name: str, year: int = 2026) -> PdfSourceRecord:
    date = "2026-06-02" if "June 2" in file_name else "2024-05-21"
    return PdfSourceRecord(
        pdf_id=f"pdf:patch:{date}",
        file_name=file_name,
        path=f"docs/knowledge_base/_sources/pdf/patch_notes/{year}/{file_name}",
        size_bytes=123,
        category="patch_note",
        year=year,
        priority="P2",
        status="pending",
        sha256="a" * 64,
    )
