import json
import shutil
from pathlib import Path
from uuid import uuid4

from gw2radar.commercial.report_engine import (
    ReportExportFormat,
    create_report_entitlement,
    ensure_default_report_products,
    generate_report_job,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.graph.graph_builder import build_mock_graph
from gw2radar.kb.kb_repository import enable_rule, list_rules
from gw2radar.kb.patch_impact_review import PatchImpactReviewInput, persist_patch_rule_candidates, save_patch_impact_review
from gw2radar.kb_pdf.patch_note_summarizer import build_recent_patch_summaries, write_patch_note_summaries
from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord
from gw2radar.kb.patch_rule_audit import PatchRuleAuditAction, record_patch_rule_audit_event


def test_patch_rule_audit_manifest_lists_source_patch_reviewer_enabled_time_and_evidence(monkeypatch) -> None:
    temp_dir = Path(".test_tmp") / f"patch-audit-manifest-{uuid4().hex}"
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
                affected_systems=["build"],
                build_impact=["Review build recommendations affected by the patch."],
                reviewer="reviewer-a",
            ),
            summary_root,
            review_store,
        )
        configure_database(f"sqlite:///{temp_dir / 'reports.db'}")
        init_db()
        with db_session.SessionLocal() as session:
            ensure_default_report_products(session)
            create_report_entitlement(session, "local-user", "legendary_gap_report")
            persisted = persist_patch_rule_candidates(session, "patch:2026-06-02", True, summary_root, review_store)
            enabled_rule = enable_rule(session, persisted.rules[0].rule_id)
            record_patch_rule_audit_event(
                PatchRuleAuditAction.ENABLE,
                patch_id="patch:2026-06-02",
                rule_id=enabled_rule.rule_id,
                reviewer="reviewer-b",
                evidence_refs=enabled_rule.evidence_refs,
            )
            rules = list_rules(session)
            job = generate_report_job(
                session,
                build_mock_graph(),
                user_id="local-user",
                product_id="legendary_gap_report",
                goal_id="gw2:goal:aurora",
                export_format=ReportExportFormat.MARKDOWN,
                output_root=temp_dir / "outputs",
                knowledge_backed=True,
                knowledge_rules=rules,
            )

        manifest = json.loads(Path(str(job.manifest_path)).read_text(encoding="utf-8"))
        audit = manifest["knowledge_base"]["patch_rule_audit"]

        assert len(audit) == 1
        assert audit[0]["source_patch_id"] == "patch:2026-06-02"
        assert audit[0]["reviewer"] == "reviewer-b"
        assert audit[0]["enabled_at"] is not None
        assert "evidence:pdf:patch:2026-06-02" in audit[0]["evidence_chain"]
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
