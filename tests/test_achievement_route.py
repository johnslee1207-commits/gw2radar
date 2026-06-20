from io import BytesIO
from pathlib import Path
from shutil import rmtree
from uuid import uuid4
from zipfile import ZipFile

from fastapi.testclient import TestClient

from gw2radar.api.main import app
from gw2radar.api.routes import achievement_routes as achievement_route_routes
from gw2radar.commercial.achievement_route import (
    AchievementRouteOperatorActionBundleRequest,
    AchievementRouteBackfillCandidateReviewRequest,
    AchievementRouteReviewedPromotionRequest,
    AchievementRouteRemediationReviewRequest,
    AchievementRouteRequest,
    AchievementRouteDraftSourcePromotionRequest,
    AchievementRouteReleaseExportBundleVerificationAuditRequest,
    AchievementRouteReleaseSignoffRequest,
    AchievementRouteSourceEditPatchApplyRequest,
    AchievementRouteSourceManifest,
    AchievementRouteStep,
    OfficialAchievementFetchPreviewRequest,
    OfficialAchievementRoutePreviewRequest,
    archive_achievement_route_release_evidence_bundle,
    build_achievement_route_backfill_candidates,
    build_achievement_route_backfill_candidate_readiness,
    build_achievement_route_release_evidence_archive_diff,
    build_achievement_route_operator_handoff_checklist,
    build_achievement_route_release_export_bundle,
    build_achievement_route_release_export_packet,
    build_achievement_route_release_readiness,
    build_achievement_route_operator_action_bundle,
    build_achievement_route_operator_release_dashboard,
    build_achievement_route_operator_release_packet,
    build_achievement_route_remediation_queue,
    build_achievement_route_remediation_readiness,
    build_achievement_route_source_edit_patch_draft,
    build_achievement_route_source_quality_review,
    build_achievement_route_unified_release_evidence_bundle,
    build_official_achievement_fetch_preview,
    build_achievement_route_plan,
    build_official_achievement_route_preview,
    apply_achievement_route_source_edit_patch_draft,
    promote_draft_achievement_route_source_to_reviewed,
    list_achievement_route_promotion_audits,
    list_achievement_route_backfill_candidate_review_audits,
    list_achievement_route_draft_source_promotion_audits,
    list_achievement_route_release_evidence_archives,
    list_achievement_route_release_signoff_audits,
    list_achievement_route_remediation_review_audits,
    list_achievement_route_source_edit_patch_apply_audits,
    load_reviewed_achievement_route_steps,
    promote_official_fetch_preview_to_reviewed_manifest,
    record_achievement_route_promotion_audit,
    record_achievement_route_backfill_candidate_review,
    record_achievement_route_remediation_review,
    record_achievement_route_release_signoff,
    render_achievement_route_backfill_candidates_csv,
    render_achievement_route_backfill_candidates_markdown,
    render_achievement_route_backfill_candidate_readiness_csv,
    render_achievement_route_backfill_candidate_readiness_markdown,
    render_achievement_route_backfill_candidate_review_audit_csv,
    render_achievement_route_backfill_candidate_review_audit_markdown,
    render_achievement_route_promotion_audit_csv,
    render_achievement_route_promotion_audit_markdown,
    render_achievement_route_operator_action_bundle_csv,
    render_achievement_route_operator_action_bundle_markdown,
    render_achievement_route_operator_release_dashboard_csv,
    render_achievement_route_operator_release_dashboard_markdown,
    render_achievement_route_operator_release_packet_csv,
    render_achievement_route_operator_release_packet_markdown,
    render_achievement_route_release_readiness_csv,
    render_achievement_route_release_readiness_markdown,
    render_achievement_route_release_evidence_archive_csv,
    render_achievement_route_release_evidence_archive_diff_csv,
    render_achievement_route_release_evidence_archive_diff_markdown,
    render_achievement_route_release_evidence_archive_markdown,
    render_achievement_route_release_export_packet_csv,
    render_achievement_route_release_export_packet_markdown,
    render_achievement_route_release_signoff_audit_csv,
    render_achievement_route_release_signoff_audit_markdown,
    render_achievement_route_remediation_queue_csv,
    render_achievement_route_remediation_queue_markdown,
    render_achievement_route_remediation_readiness_csv,
    render_achievement_route_remediation_readiness_markdown,
    render_achievement_route_remediation_review_audit_csv,
    render_achievement_route_remediation_review_audit_markdown,
    render_achievement_route_source_edit_patch_draft_csv,
    render_achievement_route_source_edit_patch_draft_markdown,
    render_achievement_route_source_edit_patch_apply_audit_csv,
    render_achievement_route_source_edit_patch_apply_audit_markdown,
    render_achievement_route_draft_source_promotion_audit_csv,
    render_achievement_route_draft_source_promotion_audit_markdown,
    render_achievement_route_unified_release_evidence_bundle_csv,
    render_achievement_route_unified_release_evidence_bundle_markdown,
    render_achievement_route_source_quality_csv,
    render_achievement_route_source_quality_markdown,
    render_official_achievement_fetch_preview_markdown,
    render_achievement_route_csv,
    render_achievement_route_markdown,
    render_official_achievement_route_preview_markdown,
    list_achievement_route_release_export_artifacts,
    list_achievement_route_release_export_bundle_verification_audits,
    resolve_achievement_route_release_export_artifact_path,
    record_achievement_route_release_export_bundle_verification_audit,
    render_achievement_route_release_export_bundle_verification_audit_csv,
    render_achievement_route_release_export_bundle_verification_audit_markdown,
    render_achievement_route_operator_handoff_checklist_csv,
    render_achievement_route_operator_handoff_checklist_markdown,
    verify_achievement_route_release_export_bundle,
    write_achievement_route_release_export_packet_artifacts,
)
from gw2radar.ingest.gateway_status import GatewayStatus
from gw2radar.ingest.gw2_api_gateway import GatewayResult


def test_achievement_route_loads_reviewed_source_manifest() -> None:
    steps, summaries = load_reviewed_achievement_route_steps()

    assert len(steps) >= 5
    assert summaries[0].source_status == "reviewed"
    assert summaries[0].step_count >= 5
    assert steps[0].source_id == "kb:achievement-routes:reviewed-seed:v1"
    assert "docs/knowledge_base/official/api_endpoints/achievements.md" in steps[0].evidence_refs


def test_official_achievement_preview_builds_draft_route_manifest() -> None:
    preview = build_official_achievement_route_preview(_official_preview_request())

    assert preview.schema_version == "gw2radar.official_achievement_route_preview.v1"
    assert preview.manifest.source_status == "draft"
    assert preview.candidate_step_count == 3
    assert "official-achievement-1002" in preview.completed_step_ids
    assert preview.manifest.steps[0].source_status == "draft"
    assert preview.manifest.steps[0].prerequisite_ids == ["achievement_api_access"]
    assert any(step.map_name == "Bloodstone Fen" for step in preview.manifest.steps)
    assert any(step.time_gate == "daily" for step in preview.manifest.steps)
    assert "Human review is required" in " ".join(preview.manifest.assumptions)
    assert "guaranteed" not in render_official_achievement_route_preview_markdown(preview).lower()


def test_official_achievement_fetch_preview_orchestrates_gateway_batch() -> None:
    request = _official_fetch_request()
    gateway = FetchPreviewGateway()

    fetch_preview = build_official_achievement_fetch_preview(request, gateway)

    assert gateway.batch_calls == [("/v2/achievements", [1001, 1002, 404])]
    assert fetch_preview.schema_version == "gw2radar.official_achievement_fetch_preview.v1"
    assert fetch_preview.fetched_achievement_ids == [1001, 1002]
    assert fetch_preview.missing_achievement_ids == [404]
    assert fetch_preview.preview.manifest.source_status == "draft"
    assert "official-achievement-1002" in fetch_preview.preview.completed_step_ids
    markdown = render_official_achievement_fetch_preview_markdown(fetch_preview)
    assert "Official Achievement Fetch Preview" in markdown
    assert "guaranteed" not in markdown.lower()


def test_promote_official_fetch_preview_requires_reviewed_gate_and_loads_manifest() -> None:
    temp_root = _temp_source_root("promotion-core")
    request = _official_fetch_request()
    fetch_preview = build_official_achievement_fetch_preview(request, FetchPreviewGateway())

    try:
        try:
            promote_official_fetch_preview_to_reviewed_manifest(
                fetch_preview,
                AchievementRouteReviewedPromotionRequest(reviewer="unit_test_operator"),
                temp_root,
            )
        except ValueError as exc:
            assert "reviewed confirmation" in str(exc)
        else:
            raise AssertionError("unconfirmed official fetch preview promotion should fail")

        result = promote_official_fetch_preview_to_reviewed_manifest(
            fetch_preview,
            AchievementRouteReviewedPromotionRequest(
                confirmed_reviewed=True,
                reviewer="unit_test_operator",
                reviewed_source_id="kb:achievement-routes:unit-official-fetch:v1",
                review_notes=["Reviewed achievement ids and route assumptions against official payload excerpts."],
            ),
            temp_root,
        )
        loaded_steps, summaries = load_reviewed_achievement_route_steps(temp_root)

        assert result.schema_version == "gw2radar.achievement_route_reviewed_promotion.v1"
        assert result.manifest.source_status == "reviewed"
        assert result.manifest.reviewed_by == "unit_test_operator"
        assert result.planner_ingestion_status == "ready"
        assert result.manifest_path.endswith("kb_achievement-routes_unit-official-fetch_v1.json")
        assert loaded_steps
        assert summaries[0].source_id == "kb:achievement-routes:unit-official-fetch:v1"
        assert all(step.source_status == "reviewed" for step in loaded_steps)
    finally:
        rmtree(temp_root, ignore_errors=True)


def test_achievement_route_promotion_audit_records_metadata_only() -> None:
    temp_root = _temp_source_root("promotion-audit-source")
    audit_root = _temp_source_root("promotion-audit-events")
    request = _official_fetch_request()
    fetch_preview = build_official_achievement_fetch_preview(request, FetchPreviewGateway())
    review = AchievementRouteReviewedPromotionRequest(
        confirmed_reviewed=True,
        reviewer="audit_operator",
        reviewed_source_id="kb:achievement-routes:audit-official-fetch:v1",
        review_notes=["Audit reviewer confirmed official ids and route assumptions."],
    )

    try:
        promotion = promote_official_fetch_preview_to_reviewed_manifest(fetch_preview, review, temp_root)
        record = record_achievement_route_promotion_audit(promotion, fetch_preview, review, audit_root)
        audit_list = list_achievement_route_promotion_audits(audit_root, reviewer="audit_operator")
        markdown = render_achievement_route_promotion_audit_markdown(audit_list)
        csv_text = render_achievement_route_promotion_audit_csv(audit_list)

        assert record.schema_version == "gw2radar.achievement_route_promotion_audit.v1"
        assert record.reviewer == "audit_operator"
        assert record.source_id == "kb:achievement-routes:audit-official-fetch:v1"
        assert record.requested_achievement_ids == [1001, 1002, 404]
        assert record.missing_achievement_ids == [404]
        assert audit_list.schema_version == "gw2radar.achievement_route_promotion_audit_list.v1"
        assert len(audit_list.records) == 1
        assert "# Achievement Route Promotion Audit" in markdown
        assert "event_id,occurred_at,reviewer,source_id" in csv_text
        assert "secret-key" not in str(audit_list).lower()
        assert "private account payload" in audit_list.boundary
    finally:
        rmtree(temp_root, ignore_errors=True)
        rmtree(audit_root, ignore_errors=True)


def test_achievement_route_release_readiness_summarizes_sources_audit_and_missing_ids() -> None:
    temp_root = _temp_source_root("release-readiness-source")
    audit_root = _temp_source_root("release-readiness-audit")
    request = _official_fetch_request()
    fetch_preview = build_official_achievement_fetch_preview(request, FetchPreviewGateway())
    review = AchievementRouteReviewedPromotionRequest(
        confirmed_reviewed=True,
        reviewer="readiness_operator",
        reviewed_source_id="kb:achievement-routes:readiness-official-fetch:v1",
        review_notes=["Readiness reviewer confirmed official ids."],
    )

    try:
        promotion = promote_official_fetch_preview_to_reviewed_manifest(fetch_preview, review, temp_root)
        no_audit = build_achievement_route_release_readiness(temp_root, audit_root)
        record_achievement_route_promotion_audit(promotion, fetch_preview, review, audit_root)
        with_missing = build_achievement_route_release_readiness(temp_root, audit_root)
        markdown = render_achievement_route_release_readiness_markdown(with_missing)
        csv_text = render_achievement_route_release_readiness_csv(with_missing)

        assert no_audit.ready is False
        assert any("No promotion audit records" in warning for warning in no_audit.warnings)
        assert with_missing.ready is False
        assert with_missing.maturity_label == "review_needed"
        assert with_missing.reviewed_source_count == 1
        assert with_missing.reviewed_step_count == 2
        assert with_missing.promotion_audit_count == 1
        assert with_missing.missing_achievement_ids == [404]
        assert "Achievement Route Release Readiness" in markdown
        assert "ready,maturity_label,readiness_score" in csv_text
        assert "secret-key" not in str(with_missing).lower()
    finally:
        rmtree(temp_root, ignore_errors=True)
        rmtree(audit_root, ignore_errors=True)


def test_achievement_route_source_quality_flags_evidence_map_gate_and_missing_id_risks() -> None:
    temp_root = _temp_source_root("source-quality")
    audit_root = _temp_source_root("source-quality-audit")
    request = _official_fetch_request()
    fetch_preview = build_official_achievement_fetch_preview(request, FetchPreviewGateway())
    review = AchievementRouteReviewedPromotionRequest(
        confirmed_reviewed=True,
        reviewer="quality_operator",
        reviewed_source_id="kb:achievement-routes:quality-official-fetch:v1",
        review_notes=["Quality reviewer checked official ids."],
    )

    try:
        promotion = promote_official_fetch_preview_to_reviewed_manifest(fetch_preview, review, temp_root)
        record_achievement_route_promotion_audit(promotion, fetch_preview, review, audit_root)
        low_quality = AchievementRouteSourceManifest(
            source_id="kb:achievement-routes:quality-risk:v1",
            title="Quality risk source",
            source_status="reviewed",
            reviewed_by="quality_operator",
            reviewed_at="2026-06-19",
            steps=[
                AchievementRouteStep(
                    step_id="quality-risk-unmapped-daily",
                    title="Unmapped daily quality risk",
                    step_type="achievement",
                    map_name="Unmapped Achievement Review",
                    region="Unknown",
                    objective="Review a daily route candidate with missing evidence.",
                    advances_goal_id="aurora_sample",
                    time_gate="daily",
                    estimated_minutes=10,
                    official_achievement_id=404,
                    assumptions=["Official achievement payload did not include an unambiguous map; review required."],
                )
            ],
        )
        (temp_root / "quality_risk.json").write_text(low_quality.model_dump_json(indent=2), encoding="utf-8")
        quality = build_achievement_route_source_quality_review(temp_root, audit_root)
        queue = build_achievement_route_remediation_queue(temp_root, audit_root)
        markdown = render_achievement_route_source_quality_markdown(quality)
        csv_text = render_achievement_route_source_quality_csv(quality)
        queue_markdown = render_achievement_route_remediation_queue_markdown(queue)
        queue_csv = render_achievement_route_remediation_queue_csv(queue)
        risk_step = next(item for item in quality.step_reviews if item.step_id == "quality-risk-unmapped-daily")

        assert quality.schema_version == "gw2radar.achievement_route_source_quality.v1"
        assert quality.maturity_label == "review_needed"
        assert risk_step.evidence_complete is False
        assert risk_step.map_inference_risk == "high"
        assert risk_step.time_gate_risk == "medium"
        assert risk_step.missing_official_id is True
        assert "missing_official_achievement_id" in risk_step.review_flags
        assert "Achievement Route Source Quality Review" in markdown
        assert "step_id,source_id,quality_score" in csv_text
        assert queue.schema_version == "gw2radar.achievement_route_remediation_queue.v1"
        assert queue.p0_count >= 1
        assert any(item.remediation_type == "official_id_backfill" for item in queue.items)
        assert any(item.remediation_type == "evidence_backfill" for item in queue.items)
        assert any(item.remediation_type == "map_review" for item in queue.items)
        assert any(item.remediation_type == "time_gate_review" for item in queue.items)
        assert "Achievement Route Remediation Queue" in queue_markdown
        assert "item_id,priority,remediation_type" in queue_csv
        assert "secret-key" not in str(quality).lower()
        assert "secret-key" not in str(queue).lower()
    finally:
        rmtree(temp_root, ignore_errors=True)
        rmtree(audit_root, ignore_errors=True)


def test_achievement_route_remediation_review_gate_records_metadata_only_audit() -> None:
    temp_root = _temp_source_root("remediation-review-source")
    audit_root = _temp_source_root("remediation-review-audit")
    request = _official_fetch_request()
    fetch_preview = build_official_achievement_fetch_preview(request, FetchPreviewGateway())
    review = AchievementRouteReviewedPromotionRequest(
        confirmed_reviewed=True,
        reviewer="remediation_operator",
        reviewed_source_id="kb:achievement-routes:remediation-review:v1",
        review_notes=["Remediation reviewer checked official ids."],
    )

    try:
        promotion = promote_official_fetch_preview_to_reviewed_manifest(fetch_preview, review, temp_root)
        record_achievement_route_promotion_audit(promotion, fetch_preview, review, audit_root)
        queue = build_achievement_route_remediation_queue(temp_root, audit_root)
        item_id = next(item.item_id for item in queue.items if item.priority == "P0")

        try:
            record_achievement_route_remediation_review(
                AchievementRouteRemediationReviewRequest(
                    item_id=item_id,
                    status="acknowledged",
                    reviewer="remediation_operator",
                    notes=["Will re-fetch official id before release."],
                ),
                temp_root,
                audit_root,
            )
        except ValueError as exc:
            assert "confirmed_manual_review" in str(exc)
        else:
            raise AssertionError("unconfirmed remediation review should fail")

        record = None
        for item in queue.items:
            record = record_achievement_route_remediation_review(
                AchievementRouteRemediationReviewRequest(
                    item_id=item.item_id,
                    status="resolved",
                    reviewer="remediation_operator",
                    notes=["Official id and route remediation were handled in the reviewed source follow-up task."],
                    evidence_refs=[f"operator-reviewed:{item.item_id}"],
                    confirmed_manual_review=True,
                ),
                temp_root,
                audit_root,
            )
        audit_list = list_achievement_route_remediation_review_audits(
            audit_root,
            reviewer="remediation_operator",
            status="resolved",
        )
        readiness = build_achievement_route_remediation_readiness(temp_root, audit_root)
        markdown = render_achievement_route_remediation_review_audit_markdown(audit_list)
        csv_text = render_achievement_route_remediation_review_audit_csv(audit_list)
        readiness_markdown = render_achievement_route_remediation_readiness_markdown(readiness)
        readiness_csv = render_achievement_route_remediation_readiness_csv(readiness)

        assert record is not None
        assert record.schema_version == "gw2radar.achievement_route_remediation_review.v1"
        assert record.status == "resolved"
        assert any(item.item_id == item_id and item.priority == "P0" for item in queue.items)
        assert record.evidence_refs
        assert audit_list.schema_version == "gw2radar.achievement_route_remediation_review_audit_list.v1"
        assert len(audit_list.records) == len(queue.items)
        assert "# Achievement Route Remediation Review Audit" in markdown
        assert "event_id,occurred_at,reviewer,status" in csv_text
        assert readiness.schema_version == "gw2radar.achievement_route_remediation_readiness.v1"
        assert readiness.ready is True
        assert readiness.maturity_label == "ready"
        assert readiness.open_p0_count == 0
        assert readiness.resolved_count == len(queue.items)
        assert "# Achievement Route Remediation Readiness" in readiness_markdown
        assert "ready,maturity_label,readiness_score" in readiness_csv
        assert "secret-key" not in str(audit_list).lower()
        assert "private account payload" in audit_list.boundary
    finally:
        rmtree(temp_root, ignore_errors=True)
        rmtree(audit_root, ignore_errors=True)


def test_achievement_route_operator_action_bundle_aggregates_and_records_review() -> None:
    temp_root = _temp_source_root("operator-action-bundle-source")
    audit_root = _temp_source_root("operator-action-bundle-audit")
    artifact_root = _temp_source_root("operator-release-export-artifacts")
    request = _official_fetch_request()
    fetch_preview = build_official_achievement_fetch_preview(request, FetchPreviewGateway())
    review = AchievementRouteReviewedPromotionRequest(
        confirmed_reviewed=True,
        reviewer="bundle_operator",
        reviewed_source_id="kb:achievement-routes:operator-bundle:v1",
        review_notes=["Bundle reviewer checked official ids."],
    )

    try:
        promotion = promote_official_fetch_preview_to_reviewed_manifest(fetch_preview, review, temp_root)
        record_achievement_route_promotion_audit(promotion, fetch_preview, review, audit_root)
        queue = build_achievement_route_remediation_queue(temp_root, audit_root)
        item_id = queue.items[0].item_id

        initial = build_achievement_route_operator_action_bundle(None, temp_root, audit_root)
        updated = build_achievement_route_operator_action_bundle(
            AchievementRouteOperatorActionBundleRequest(
                review=AchievementRouteRemediationReviewRequest(
                    item_id=item_id,
                    status="acknowledged",
                    reviewer="bundle_operator",
                    notes=["Acknowledged from operator bundle."],
                    evidence_refs=["official:/v2/achievements"],
                    confirmed_manual_review=True,
                )
            ),
            temp_root,
            audit_root,
        )
        markdown = render_achievement_route_operator_action_bundle_markdown(updated)
        csv_text = render_achievement_route_operator_action_bundle_csv(updated)
        packet = build_achievement_route_operator_release_packet(temp_root, audit_root)
        packet_markdown = render_achievement_route_operator_release_packet_markdown(packet)
        packet_csv = render_achievement_route_operator_release_packet_csv(packet)
        candidates = build_achievement_route_backfill_candidates(temp_root, audit_root)
        candidates_markdown = render_achievement_route_backfill_candidates_markdown(candidates)
        candidates_csv = render_achievement_route_backfill_candidates_csv(candidates)
        candidate_id = next(candidate.candidate_id for candidate in candidates.candidates if candidate.step_id)
        try:
            record_achievement_route_backfill_candidate_review(
                AchievementRouteBackfillCandidateReviewRequest(
                    candidate_id=candidate_id,
                    status="acknowledged",
                    reviewer="bundle_operator",
                    confirmed_manual_review=False,
                ),
                temp_root,
                audit_root,
            )
        except ValueError as exc:
            assert "confirmed_manual_review" in str(exc)
        else:
            raise AssertionError("unconfirmed backfill candidate review should fail")
        candidate_record = record_achievement_route_backfill_candidate_review(
            AchievementRouteBackfillCandidateReviewRequest(
                candidate_id=candidate_id,
                status="acknowledged",
                reviewer="bundle_operator",
                notes=["Candidate was acknowledged for manual source editing."],
                evidence_refs=["operator-review:backfill-candidate"],
                confirmed_manual_review=True,
            ),
            temp_root,
            audit_root,
        )
        candidate_audit = list_achievement_route_backfill_candidate_review_audits(
            audit_root,
            reviewer="bundle_operator",
        )
        candidate_readiness = build_achievement_route_backfill_candidate_readiness(temp_root, audit_root)
        candidate_audit_markdown = render_achievement_route_backfill_candidate_review_audit_markdown(candidate_audit)
        candidate_audit_csv = render_achievement_route_backfill_candidate_review_audit_csv(candidate_audit)
        candidate_readiness_markdown = render_achievement_route_backfill_candidate_readiness_markdown(candidate_readiness)
        candidate_readiness_csv = render_achievement_route_backfill_candidate_readiness_csv(candidate_readiness)
        resolved_candidate_record = record_achievement_route_backfill_candidate_review(
            AchievementRouteBackfillCandidateReviewRequest(
                candidate_id=candidate_id,
                status="resolved",
                reviewer="bundle_operator",
                notes=["Candidate fields are ready for a manual source edit patch draft."],
                evidence_refs=["operator-review:source-edit-patch-draft"],
                confirmed_manual_review=True,
            ),
            temp_root,
            audit_root,
        )
        patch_draft = build_achievement_route_source_edit_patch_draft(temp_root, audit_root)
        patch_markdown = render_achievement_route_source_edit_patch_draft_markdown(patch_draft)
        patch_csv = render_achievement_route_source_edit_patch_draft_csv(patch_draft)
        draft_id = patch_draft.drafts[0].draft_id
        try:
            apply_achievement_route_source_edit_patch_draft(
                AchievementRouteSourceEditPatchApplyRequest(
                    draft_id=draft_id,
                    reviewer="bundle_operator",
                    confirmed_manual_review=False,
                ),
                temp_root,
                audit_root,
            )
        except ValueError as exc:
            assert "confirmed_manual_review" in str(exc)
        else:
            raise AssertionError("unconfirmed source edit patch apply should fail")
        apply_record = apply_achievement_route_source_edit_patch_draft(
            AchievementRouteSourceEditPatchApplyRequest(
                draft_id=draft_id,
                reviewer="bundle_operator",
                notes=["Applied patch draft into a draft manifest for later promotion review."],
                evidence_refs=["operator-review:source-edit-patch-apply"],
                confirmed_manual_review=True,
            ),
            temp_root,
            audit_root,
        )
        apply_audit = list_achievement_route_source_edit_patch_apply_audits(
            audit_root,
            reviewer="bundle_operator",
        )
        apply_audit_markdown = render_achievement_route_source_edit_patch_apply_audit_markdown(apply_audit)
        apply_audit_csv = render_achievement_route_source_edit_patch_apply_audit_csv(apply_audit)
        try:
            promote_draft_achievement_route_source_to_reviewed(
                AchievementRouteDraftSourcePromotionRequest(
                    draft_source_id=apply_record.output_source_id,
                    reviewer="bundle_operator",
                    confirmed_reviewed=False,
                ),
                temp_root,
                audit_root,
            )
        except ValueError as exc:
            assert "confirmed_reviewed" in str(exc)
        else:
            raise AssertionError("unconfirmed draft source promotion should fail")
        draft_promotion = promote_draft_achievement_route_source_to_reviewed(
            AchievementRouteDraftSourcePromotionRequest(
                draft_source_id=apply_record.output_source_id,
                reviewer="bundle_operator",
                review_notes=["Promoted draft source manifest after patch apply review."],
                evidence_refs=["operator-review:draft-source-promotion"],
                overwrite_existing=True,
                confirmed_reviewed=True,
            ),
            temp_root,
            audit_root,
        )
        draft_promotion_audit = list_achievement_route_draft_source_promotion_audits(
            audit_root,
            reviewer="bundle_operator",
        )
        draft_promotion_markdown = render_achievement_route_draft_source_promotion_audit_markdown(draft_promotion_audit)
        draft_promotion_csv = render_achievement_route_draft_source_promotion_audit_csv(draft_promotion_audit)
        promoted_steps, promoted_summaries = load_reviewed_achievement_route_steps(temp_root)
        evidence_bundle = build_achievement_route_unified_release_evidence_bundle(temp_root, audit_root)
        evidence_markdown = render_achievement_route_unified_release_evidence_bundle_markdown(evidence_bundle)
        evidence_csv = render_achievement_route_unified_release_evidence_bundle_csv(evidence_bundle)
        archive_record = archive_achievement_route_release_evidence_bundle(
            temp_root,
            audit_root,
            archived_by="bundle_operator",
            retention_policy="retain_365_days",
        )
        archive_record_second = archive_achievement_route_release_evidence_bundle(
            temp_root,
            audit_root,
            archived_by="bundle_operator",
            retention_policy="retain_365_days",
        )
        archive_index = list_achievement_route_release_evidence_archives(audit_root, archived_by="bundle_operator")
        archive_markdown = render_achievement_route_release_evidence_archive_markdown(archive_index)
        archive_csv = render_achievement_route_release_evidence_archive_csv(archive_index)
        archive_diff = build_achievement_route_release_evidence_archive_diff(audit_root)
        archive_diff_markdown = render_achievement_route_release_evidence_archive_diff_markdown(archive_diff)
        archive_diff_csv = render_achievement_route_release_evidence_archive_diff_csv(archive_diff)
        try:
            record_achievement_route_release_signoff(
                AchievementRouteReleaseSignoffRequest(
                    reviewer="bundle_operator",
                    notes=["Unconfirmed release sign-off should fail."],
                    confirmed_signoff=False,
                ),
                temp_root,
                audit_root,
            )
        except ValueError as exc:
            assert "confirmed_signoff" in str(exc)
        else:
            raise AssertionError("unconfirmed release sign-off should fail")
        signoff_record = record_achievement_route_release_signoff(
            AchievementRouteReleaseSignoffRequest(
                reviewer="bundle_operator",
                notes=["Release evidence, archive, and diff reviewed."],
                evidence_refs=["operator-review:release-signoff"],
                confirmed_signoff=True,
            ),
            temp_root,
            audit_root,
        )
        signoff_audit = list_achievement_route_release_signoff_audits(audit_root, reviewer="bundle_operator")
        signoff_markdown = render_achievement_route_release_signoff_audit_markdown(signoff_audit)
        signoff_csv = render_achievement_route_release_signoff_audit_csv(signoff_audit)
        release_dashboard = build_achievement_route_operator_release_dashboard(temp_root, audit_root)
        release_dashboard_markdown = render_achievement_route_operator_release_dashboard_markdown(release_dashboard)
        release_dashboard_csv = render_achievement_route_operator_release_dashboard_csv(release_dashboard)
        release_export_packet = build_achievement_route_release_export_packet(temp_root, audit_root)
        release_export_packet_markdown = render_achievement_route_release_export_packet_markdown(release_export_packet)
        release_export_packet_csv = render_achievement_route_release_export_packet_csv(release_export_packet)
        release_export_artifacts = write_achievement_route_release_export_packet_artifacts(temp_root, audit_root, artifact_root)
        release_export_artifact_index = list_achievement_route_release_export_artifacts(artifact_root)
        release_export_artifact_path = resolve_achievement_route_release_export_artifact_path(
            release_export_artifacts.files[0].relative_path,
            artifact_root,
        )
        release_export_bundle_manifest, release_export_bundle_bytes = build_achievement_route_release_export_bundle(artifact_root)
        release_export_bundle_names = set(ZipFile(BytesIO(release_export_bundle_bytes)).namelist())
        release_export_bundle_verification = verify_achievement_route_release_export_bundle(
            release_export_bundle_bytes,
            expected_checksum_sha256=release_export_bundle_manifest.checksum_sha256,
        )
        tampered_bundle_buffer = BytesIO()
        with ZipFile(BytesIO(release_export_bundle_bytes), mode="r") as source_archive:
            with ZipFile(tampered_bundle_buffer, mode="w") as tampered_archive:
                for name in source_archive.namelist():
                    tampered_archive.writestr(name, source_archive.read(name))
                tampered_archive.writestr("achievement_route_release_export/extra.txt", "not allowed")
        tampered_bundle_verification = verify_achievement_route_release_export_bundle(
            tampered_bundle_buffer.getvalue(),
            expected_checksum_sha256=release_export_bundle_manifest.checksum_sha256,
        )
        release_export_bundle_audit_record = record_achievement_route_release_export_bundle_verification_audit(
            AchievementRouteReleaseExportBundleVerificationAuditRequest(
                reviewer="operator_action_bundle_test",
                notes=["Unit test recorded release bundle verification audit."],
            ),
            release_export_bundle_bytes,
            temp_root,
            audit_root,
            artifact_root,
        )
        release_export_bundle_audit = list_achievement_route_release_export_bundle_verification_audits(
            audit_root,
            reviewer="operator_action_bundle_test",
        )
        release_export_bundle_audit_markdown = render_achievement_route_release_export_bundle_verification_audit_markdown(
            release_export_bundle_audit
        )
        release_export_bundle_audit_csv = render_achievement_route_release_export_bundle_verification_audit_csv(
            release_export_bundle_audit
        )
        operator_handoff = build_achievement_route_operator_handoff_checklist(temp_root, audit_root, artifact_root)
        operator_handoff_markdown = render_achievement_route_operator_handoff_checklist_markdown(operator_handoff)
        operator_handoff_csv = render_achievement_route_operator_handoff_checklist_csv(operator_handoff)

        assert initial.schema_version == "gw2radar.achievement_route_operator_action_bundle.v1"
        assert initial.remediation_review is None
        assert initial.remediation_queue.open_item_count >= 1
        assert updated.remediation_review is not None
        assert updated.remediation_review.item_id == item_id
        assert updated.remediation_review.status == "acknowledged"
        assert updated.remediation_review_audit.records[0].item_id == item_id
        assert updated.remediation_readiness.open_p0_count >= 1
        assert "Achievement Route Operator Action Bundle" in markdown
        assert "quality_maturity,quality_score,queue_item_count" in csv_text
        assert packet.schema_version == "gw2radar.achievement_route_operator_release_packet.v1"
        assert packet.manifest["packet_schema"] == packet.schema_version
        assert "operator_release_packet_manifest.json" in packet.manifest["artifacts"]
        assert "Achievement Route Operator Release Packet" in packet_markdown
        assert "packet_id,ready,maturity_label" in packet_csv
        assert candidates.schema_version == "gw2radar.achievement_route_backfill_candidates.v1"
        assert candidates.candidate_count >= 1
        assert candidates.candidates[0].suggested_fields
        assert "Achievement Route Backfill Candidates" in candidates_markdown
        assert "candidate_id,item_id,priority" in candidates_csv
        assert candidate_record.schema_version == "gw2radar.achievement_route_backfill_candidate_review.v1"
        assert candidate_record.candidate_id == candidate_id
        assert candidate_record.status == "acknowledged"
        assert candidate_audit.schema_version == "gw2radar.achievement_route_backfill_candidate_review_audit_list.v1"
        assert candidate_audit.records[0].candidate_id == candidate_id
        assert candidate_readiness.schema_version == "gw2radar.achievement_route_backfill_candidate_readiness.v1"
        assert candidate_readiness.open_candidate_count >= 1
        assert "Achievement Route Backfill Candidate Review Audit" in candidate_audit_markdown
        assert "candidate_id,item_id" in candidate_audit_csv
        assert "Achievement Route Backfill Candidate Readiness" in candidate_readiness_markdown
        assert "ready,maturity_label,readiness_score" in candidate_readiness_csv
        assert resolved_candidate_record.status == "resolved"
        assert patch_draft.schema_version == "gw2radar.achievement_route_source_edit_patch_draft.v1"
        assert patch_draft.draft_count >= 1
        assert patch_draft.operation_count >= 1
        assert patch_draft.drafts[0].candidate_id == candidate_id
        assert patch_draft.drafts[0].operations[0].required_review
        assert "Achievement Route Source Edit Patch Draft" in patch_markdown
        assert "draft_id,candidate_id,item_id" in patch_csv
        assert apply_record.schema_version == "gw2radar.achievement_route_source_edit_patch_apply.v1"
        assert apply_record.draft_id == draft_id
        assert apply_record.operation_count >= 1
        assert Path(apply_record.output_manifest_path).exists()
        assert ":patch-draft:" in apply_record.output_source_id
        assert apply_audit.schema_version == "gw2radar.achievement_route_source_edit_patch_apply_audit_list.v1"
        assert apply_audit.records[0].draft_id == draft_id
        assert "# Achievement Route Source Edit Patch Apply Audit" in apply_audit_markdown
        assert "event_id,applied_at,reviewer,draft_id" in apply_audit_csv
        assert draft_promotion.schema_version == "gw2radar.achievement_route_draft_source_promotion.v1"
        assert draft_promotion.draft_source_id == apply_record.output_source_id
        assert draft_promotion.reviewed_source_id.endswith(":reviewed")
        assert draft_promotion.planner_ingestion_status == "ready"
        assert draft_promotion_audit.schema_version == "gw2radar.achievement_route_draft_source_promotion_audit_list.v1"
        assert draft_promotion_audit.records[0].draft_source_id == apply_record.output_source_id
        assert "# Achievement Route Draft Source Promotion Audit" in draft_promotion_markdown
        assert "event_id,promoted_at,reviewer,draft_source_id" in draft_promotion_csv
        assert any(summary.source_id == draft_promotion.reviewed_source_id for summary in promoted_summaries)
        assert any(step.source_id == draft_promotion.reviewed_source_id for step in promoted_steps)
        assert evidence_bundle.schema_version == "gw2radar.achievement_route_unified_release_evidence_bundle.v1"
        assert evidence_bundle.reviewed_source_count >= 2
        assert evidence_bundle.official_promotion_audit_count >= 1
        assert evidence_bundle.patch_apply_audit_count >= 1
        assert evidence_bundle.draft_source_promotion_audit_count >= 1
        assert evidence_bundle.manifest["bundle_schema"] == evidence_bundle.schema_version
        assert "unified_release_evidence_bundle_manifest.json" in evidence_bundle.artifacts
        assert "Achievement Route Unified Release Evidence Bundle" in evidence_markdown
        assert "bundle_id,ready,maturity_label" in evidence_csv
        assert archive_record.schema_version == "gw2radar.achievement_route_release_evidence_archive_record.v1"
        assert archive_record.archived_by == "bundle_operator"
        assert archive_record.retention_policy == "retain_365_days"
        assert archive_record.source_bundle_schema == evidence_bundle.schema_version
        assert len(archive_record.checksum_sha256) == 64
        assert archive_record.manifest_schema == "gw2radar.achievement_route_unified_release_evidence_bundle.v1"
        assert archive_index.schema_version == "gw2radar.achievement_route_release_evidence_archive_index.v1"
        assert archive_record_second.archive_id != archive_record.archive_id
        assert archive_index.total_records == 2
        assert archive_index.records[0].archive_id == archive_record_second.archive_id
        assert "# Achievement Route Release Evidence Archive" in archive_markdown
        assert "archive_id,bundle_id,archived_at" in archive_csv
        assert archive_diff.schema_version == "gw2radar.achievement_route_release_evidence_archive_diff.v1"
        assert archive_diff.baseline_archive_id == archive_record.archive_id
        assert archive_diff.candidate_archive_id == archive_record_second.archive_id
        assert archive_diff.regression_count == 0
        assert archive_diff.checksum_changed
        assert "Achievement Route Release Evidence Archive Diff" in archive_diff_markdown
        assert "baseline_archive_id,candidate_archive_id,ready" in archive_diff_csv
        assert signoff_record.schema_version == "gw2radar.achievement_route_release_signoff.v1"
        assert signoff_record.reviewer == "bundle_operator"
        assert signoff_record.archive_id == archive_record_second.archive_id
        assert signoff_record.regression_count == 0
        assert signoff_audit.schema_version == "gw2radar.achievement_route_release_signoff_audit_list.v1"
        assert signoff_audit.records[0].signoff_id == signoff_record.signoff_id
        assert "# Achievement Route Release Sign-off Audit" in signoff_markdown
        assert "signoff_id,signed_off_at,reviewer,status" in signoff_csv
        assert release_dashboard.schema_version == "gw2radar.achievement_route_operator_release_dashboard.v1"
        assert release_dashboard.archive_count == 2
        assert release_dashboard.latest_archive_id == archive_record_second.archive_id
        assert release_dashboard.diff_regression_count == 0
        assert release_dashboard.latest_signoff_id == signoff_record.signoff_id
        assert "Achievement Route Operator Release Dashboard" in release_dashboard_markdown
        assert "ready,maturity_label,bundle_id" in release_dashboard_csv
        assert release_export_packet.schema_version == "gw2radar.achievement_route_release_export_packet.v1"
        assert release_export_packet.dashboard_schema == release_dashboard.schema_version
        assert release_export_packet.bundle_id == release_dashboard.bundle_id
        assert release_export_packet.latest_archive_id == release_dashboard.latest_archive_id
        assert release_export_packet.latest_signoff_id == signoff_record.signoff_id
        assert "release_export_packet_manifest.json" in release_export_packet.artifacts
        assert release_export_packet.manifest["packet_schema"] == release_export_packet.schema_version
        assert "Achievement Route Release Export Packet" in release_export_packet_markdown
        assert "packet_id,ready,maturity_label" in release_export_packet_csv
        assert release_export_artifacts.schema_version == "gw2radar.achievement_route_release_export_artifact_index.v1"
        assert release_export_artifacts.file_count == 3
        assert {file.filename for file in release_export_artifacts.files} == {
            "release_export_packet_manifest.json",
            "release_export_packet.md",
            "release_export_packet.csv",
        }
        assert release_export_artifact_index.file_count == 3
        assert release_export_artifact_path is not None
        assert release_export_artifact_path.exists()
        assert resolve_achievement_route_release_export_artifact_path("../secret.txt", artifact_root) is None
        assert release_export_bundle_manifest.schema_version == "gw2radar.achievement_route_release_export_bundle_manifest.v1"
        assert release_export_bundle_manifest.file_count == 4
        assert release_export_bundle_manifest.size_bytes == len(release_export_bundle_bytes)
        assert release_export_bundle_manifest.checksum_sha256
        assert release_export_bundle_names == {
            "achievement_route_release_export/artifact_index.json",
            "achievement_route_release_export/release_export_packet_manifest.json",
            "achievement_route_release_export/release_export_packet.md",
            "achievement_route_release_export/release_export_packet.csv",
        }
        assert release_export_bundle_verification.schema_version == "gw2radar.achievement_route_release_export_bundle_verification.v1"
        assert release_export_bundle_verification.ready is True
        assert release_export_bundle_verification.file_count == 4
        assert release_export_bundle_verification.blockers == []
        assert tampered_bundle_verification.ready is False
        assert any("checksum" in blocker for blocker in tampered_bundle_verification.blockers)
        assert any("non-whitelisted" in blocker for blocker in tampered_bundle_verification.blockers)
        assert release_export_bundle_audit_record.schema_version == "gw2radar.achievement_route_release_export_bundle_verification_audit.v1"
        assert release_export_bundle_audit_record.ready is True
        assert release_export_bundle_audit_record.reviewer == "operator_action_bundle_test"
        assert release_export_bundle_audit.records[0].audit_id == release_export_bundle_audit_record.audit_id
        assert "Achievement Route Release Bundle Verification Audit" in release_export_bundle_audit_markdown
        assert "audit_id,verified_at,reviewer,ready,checksum_sha256" in release_export_bundle_audit_csv
        assert operator_handoff.schema_version == "gw2radar.achievement_route_operator_handoff_checklist.v1"
        assert operator_handoff.ready is True
        assert operator_handoff.maturity_label == "ready"
        assert operator_handoff.packet_artifact_count == 3
        assert operator_handoff.bundle_file_count == 4
        assert operator_handoff.verification_ready is True
        assert operator_handoff.verification_audit_count == 1
        assert "Achievement Route Operator Handoff Checklist" in operator_handoff_markdown
        assert "ready,maturity_label,packet_id,packet_artifact_count" in operator_handoff_csv
        assert "secret-key" not in str(updated).lower()
        assert "secret-key" not in str(packet).lower()
        assert "secret-key" not in str(candidates).lower()
        assert "secret-key" not in str(candidate_audit).lower()
        assert "secret-key" not in str(patch_draft).lower()
        assert "secret-key" not in str(apply_audit).lower()
        assert "secret-key" not in str(draft_promotion_audit).lower()
        assert "secret-key" not in str(evidence_bundle).lower()
        assert "secret-key" not in str(archive_index).lower()
        assert "secret-key" not in str(archive_diff).lower()
        assert "secret-key" not in str(signoff_audit).lower()
        assert "secret-key" not in str(release_dashboard).lower()
        assert "secret-key" not in str(release_export_packet).lower()
        assert "secret-key" not in str(release_export_artifacts).lower()
        assert "secret-key" not in str(release_export_bundle_verification).lower()
        assert "secret-key" not in str(release_export_bundle_audit).lower()
        assert "secret-key" not in str(operator_handoff).lower()
        assert "secret-key" not in release_export_bundle_bytes.decode("latin1").lower()
    finally:
        rmtree(temp_root, ignore_errors=True)
        rmtree(audit_root, ignore_errors=True)
        rmtree(artifact_root, ignore_errors=True)


def test_achievement_route_groups_ready_blocked_and_time_gated_steps() -> None:
    plan = build_achievement_route_plan(
        AchievementRouteRequest(
            goal_id="all",
            available_minutes=30,
            unlocked_prerequisite_ids=["living_world_s3_access", "achievement_api_access"],
            include_group_content=False,
        )
    )

    assert "aurora-bloodstone-fen-reviewed-sweep" in plan.ready_step_ids
    assert "aurora-ember-bay-reviewed-daily" in plan.time_gated_step_ids
    assert "vision-dragonfall-reviewed-meta-check" in plan.blocked_step_ids
    assert plan.source_ids == ["kb:achievement-routes:reviewed-seed:v1"]
    assert plan.segments[0].ready_step_ids
    assert all(action.manual_only for action in plan.next_actions)
    assert any("in-game achievement panel" in assumption for assumption in plan.assumptions)
    assert "guaranteed" not in render_achievement_route_markdown(plan).lower()


def test_achievement_route_markdown_and_csv_exports_are_deterministic() -> None:
    plan = build_achievement_route_plan(
        AchievementRouteRequest(
            goal_id="aurora_sample",
            available_minutes=45,
            unlocked_prerequisite_ids=["living_world_s3_access", "achievement_api_access"],
        )
    )

    markdown = render_achievement_route_markdown(plan)
    csv_text = render_achievement_route_csv(plan)

    assert "# Achievement & Collection Route Plan" in markdown
    assert "## Assumptions" in markdown
    assert "## Source Warnings" in markdown
    assert "Manual planning only" in markdown
    assert csv_text.splitlines()[0].startswith("step_id,title,map_name")
    assert "aurora-ember-bay-reviewed-daily" in csv_text
    assert "kb:achievement-routes:reviewed-seed:v1" in csv_text


def test_achievement_route_api_plan_and_exports() -> None:
    client = TestClient(app)
    request = {
        "goal_id": "all",
        "available_minutes": 40,
        "unlocked_prerequisite_ids": ["living_world_s3_access", "living_world_s4_access", "achievement_api_access"],
        "include_group_content": True,
    }

    sources = client.get("/api/v1/achievement-routes/sources")
    planned = client.post("/api/v1/achievement-routes/plan", json=request)
    markdown = client.post("/api/v1/achievement-routes/plan/export?format=markdown", json=request)
    csv_response = client.post("/api/v1/achievement-routes/plan/export?format=csv", json=request)

    assert sources.status_code == 200
    assert sources.json()["data"]["reviewed_step_count"] >= 5
    assert planned.status_code == 200
    assert planned.json()["data"]["plan"]["schema_version"] == "gw2radar.achievement_route_plan.v1"
    assert planned.json()["data"]["plan"]["source_ids"] == ["kb:achievement-routes:reviewed-seed:v1"]
    assert markdown.status_code == 200
    assert "Route Segments" in markdown.text
    assert csv_response.status_code == 200
    assert "status,time_gate" in csv_response.text


def test_official_achievement_preview_api_and_exports() -> None:
    client = TestClient(app)
    request = _official_preview_request().model_dump(mode="json")

    preview = client.post("/api/v1/achievement-routes/official-preview", json=request)
    markdown = client.post("/api/v1/achievement-routes/official-preview/export?format=markdown", json=request)
    json_export = client.post("/api/v1/achievement-routes/official-preview/export?format=json", json=request)

    assert preview.status_code == 200
    payload = preview.json()["data"]["preview"]
    assert payload["manifest"]["source_status"] == "draft"
    assert payload["candidate_step_count"] == 3
    assert payload["manifest"]["steps"][0]["evidence_refs"]
    assert markdown.status_code == 200
    assert "Official Achievement Route Preview" in markdown.text
    assert json_export.status_code == 200
    assert "official:achievement-route-preview:test" in json_export.text


def test_official_achievement_fetch_preview_api_and_exports() -> None:
    original_factory = achievement_route_routes.gateway_factory
    achievement_route_routes.gateway_factory = FetchPreviewGateway
    try:
        client = TestClient(app)
        request = _official_fetch_request().model_dump(mode="json")

        preview = client.post("/api/v1/achievement-routes/official-fetch-preview", json=request)
        markdown = client.post("/api/v1/achievement-routes/official-fetch-preview/export?format=markdown", json=request)
        json_export = client.post("/api/v1/achievement-routes/official-fetch-preview/export?format=json", json=request)

        assert preview.status_code == 200
        payload = preview.json()["data"]["fetch_preview"]
        assert payload["preview"]["manifest"]["source_status"] == "draft"
        assert payload["fetched_achievement_ids"] == [1001, 1002]
        assert payload["missing_achievement_ids"] == [404]
        assert "secret-key" not in str(payload).lower()
        assert markdown.status_code == 200
        assert "Official Achievement Fetch Preview" in markdown.text
        assert json_export.status_code == 200
        assert "official:achievement-route-fetch-preview:test" in json_export.text
    finally:
        achievement_route_routes.gateway_factory = original_factory


def test_official_achievement_fetch_preview_promote_reviewed_api() -> None:
    temp_root = _temp_source_root("promotion-api")
    audit_root = _temp_source_root("promotion-api-audit")
    release_export_root = _temp_source_root("promotion-api-release-export")
    original_factory = achievement_route_routes.gateway_factory
    original_source_root = achievement_route_routes.source_root
    original_audit_root = achievement_route_routes.audit_root
    original_release_export_root = achievement_route_routes.release_export_root
    achievement_route_routes.gateway_factory = FetchPreviewGateway
    achievement_route_routes.source_root = temp_root
    achievement_route_routes.audit_root = audit_root
    achievement_route_routes.release_export_root = release_export_root
    try:
        client = TestClient(app)
        request = _official_fetch_request().model_dump(mode="json")
        review = {
            "confirmed_reviewed": True,
            "reviewer": "api_review_operator",
            "reviewed_source_id": "kb:achievement-routes:api-official-fetch:v1",
            "review_notes": ["API reviewer confirmed route candidate assumptions."],
        }

        blocked = client.post(
            "/api/v1/achievement-routes/official-fetch-preview/promote-reviewed",
            json={"request": request, "review": {**review, "confirmed_reviewed": False}},
        )
        promoted = client.post(
            "/api/v1/achievement-routes/official-fetch-preview/promote-reviewed",
            json={"request": request, "review": review},
        )
        sources = client.get("/api/v1/achievement-routes/sources")
        plan = client.post(
            "/api/v1/achievement-routes/plan",
            json={
                "goal_id": "aurora_sample",
                "available_minutes": 40,
                "unlocked_prerequisite_ids": ["achievement_api_access"],
            },
        )
        audit = client.get("/api/v1/achievement-routes/promotion-audit?reviewer=api_review_operator&limit=5")
        audit_markdown = client.get("/api/v1/achievement-routes/promotion-audit?reviewer=api_review_operator&format=markdown")
        audit_csv = client.get("/api/v1/achievement-routes/promotion-audit?reviewer=api_review_operator&format=csv")
        readiness = client.get("/api/v1/achievement-routes/release-readiness")
        readiness_markdown = client.get("/api/v1/achievement-routes/release-readiness?format=markdown")
        readiness_csv = client.get("/api/v1/achievement-routes/release-readiness?format=csv")
        quality = client.get("/api/v1/achievement-routes/source-quality")
        quality_markdown = client.get("/api/v1/achievement-routes/source-quality?format=markdown")
        quality_csv = client.get("/api/v1/achievement-routes/source-quality?format=csv")
        remediation_queue = client.get("/api/v1/achievement-routes/source-quality/remediation-queue")
        remediation_markdown = client.get("/api/v1/achievement-routes/source-quality/remediation-queue?format=markdown")
        remediation_csv = client.get("/api/v1/achievement-routes/source-quality/remediation-queue?format=csv")

        assert blocked.status_code == 400
        assert promoted.status_code == 200
        promotion = promoted.json()["data"]["promotion"]
        audit_record = promoted.json()["data"]["audit_record"]
        assert promotion["manifest"]["source_status"] == "reviewed"
        assert promotion["manifest"]["reviewed_by"] == "api_review_operator"
        assert audit_record["reviewer"] == "api_review_operator"
        assert audit_record["source_id"] == "kb:achievement-routes:api-official-fetch:v1"
        assert "secret-key" not in str(promotion).lower()
        assert "secret-key" not in str(audit.json()).lower()
        assert sources.json()["data"]["reviewed_step_count"] == 2
        assert plan.json()["data"]["plan"]["source_ids"] == ["kb:achievement-routes:api-official-fetch:v1"]
        assert audit.json()["data"]["audit"]["records"][0]["source_id"] == "kb:achievement-routes:api-official-fetch:v1"
        assert "# Achievement Route Promotion Audit" in audit_markdown.text
        assert "event_id,occurred_at,reviewer,source_id" in audit_csv.text
        assert readiness.status_code == 200
        assert readiness.json()["data"]["readiness"]["promotion_audit_count"] == 1
        assert readiness.json()["data"]["readiness"]["missing_achievement_ids"] == [404]
        assert "# Achievement Route Release Readiness" in readiness_markdown.text
        assert "ready,maturity_label,readiness_score" in readiness_csv.text
        assert quality.status_code == 200
        assert quality.json()["data"]["quality"]["source_reviews"][0]["source_id"] == "kb:achievement-routes:api-official-fetch:v1"
        assert "# Achievement Route Source Quality Review" in quality_markdown.text
        assert "step_id,source_id,quality_score" in quality_csv.text
        assert remediation_queue.status_code == 200
        assert remediation_queue.json()["data"]["remediation_queue"]["p0_count"] >= 1
        assert "# Achievement Route Remediation Queue" in remediation_markdown.text
        assert "item_id,priority,remediation_type" in remediation_csv.text
        remediation_item_id = remediation_queue.json()["data"]["remediation_queue"]["items"][0]["item_id"]
        blocked_review = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/review",
            json={
                "item_id": remediation_item_id,
                "status": "acknowledged",
                "reviewer": "api_review_operator",
                "notes": ["Reviewed from API test."],
                "confirmed_manual_review": False,
            },
        )
        review_action = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/review",
            json={
                "item_id": remediation_item_id,
                "status": "acknowledged",
                "reviewer": "api_review_operator",
                "notes": ["Acknowledged missing official id remediation."],
                "evidence_refs": ["official:/v2/achievements"],
                "confirmed_manual_review": True,
            },
        )
        review_audit = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/review-audit?reviewer=api_review_operator")
        review_audit_markdown = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/review-audit?format=markdown")
        review_audit_csv = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/review-audit?format=csv")
        remediation_readiness = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/readiness")
        remediation_readiness_markdown = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/readiness?format=markdown")
        remediation_readiness_csv = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/readiness?format=csv")
        action_bundle = client.post("/api/v1/achievement-routes/source-quality/remediation-queue/action-bundle", json={})
        action_bundle_review = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/action-bundle",
            json={
                "review": {
                    "item_id": remediation_item_id,
                    "status": "resolved",
                    "reviewer": "api_review_operator",
                    "notes": ["Resolved through operator action bundle."],
                    "evidence_refs": ["official:/v2/achievements?action-bundle"],
                    "confirmed_manual_review": True,
                }
            },
        )
        action_bundle_markdown = client.post("/api/v1/achievement-routes/source-quality/remediation-queue/action-bundle?format=markdown", json={})
        action_bundle_csv = client.post("/api/v1/achievement-routes/source-quality/remediation-queue/action-bundle?format=csv", json={})
        release_packet = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-packet")
        release_packet_markdown = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-packet?format=markdown")
        release_packet_csv = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-packet?format=csv")
        release_packet_manifest = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-packet?format=manifest")
        backfill_candidates = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates")
        backfill_candidates_markdown = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates?format=markdown")
        backfill_candidates_csv = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates?format=csv")
        backfill_candidate_id = next(
            candidate["candidate_id"]
            for candidate in backfill_candidates.json()["data"]["backfill_candidates"]["candidates"]
            if candidate.get("step_id")
        )
        blocked_backfill_review = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/review",
            json={
                "candidate_id": backfill_candidate_id,
                "status": "acknowledged",
                "reviewer": "api_review_operator",
                "notes": ["Reviewed from API test."],
                "confirmed_manual_review": False,
            },
        )
        backfill_review = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/review",
            json={
                "candidate_id": backfill_candidate_id,
                "status": "acknowledged",
                "reviewer": "api_review_operator",
                "notes": ["Acknowledged candidate for manual source editing."],
                "evidence_refs": ["official:/v2/achievements?backfill-candidate"],
                "confirmed_manual_review": True,
            },
        )
        backfill_audit = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/review-audit?reviewer=api_review_operator"
        )
        backfill_audit_markdown = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/review-audit?format=markdown"
        )
        backfill_audit_csv = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/review-audit?format=csv"
        )
        backfill_readiness = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/readiness")
        backfill_readiness_markdown = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/readiness?format=markdown"
        )
        backfill_readiness_csv = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/readiness?format=csv")
        backfill_resolved_review = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/review",
            json={
                "candidate_id": backfill_candidate_id,
                "status": "resolved",
                "reviewer": "api_review_operator",
                "notes": ["Resolved candidate is ready for source edit patch draft."],
                "evidence_refs": ["official:/v2/achievements?source-edit-patch"],
                "confirmed_manual_review": True,
            },
        )
        source_patch_draft = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft"
        )
        source_patch_draft_markdown = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft?format=markdown"
        )
        source_patch_draft_csv = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft?format=csv"
        )
        source_patch_draft_id = source_patch_draft.json()["data"]["source_edit_patch_draft"]["drafts"][0]["draft_id"]
        blocked_patch_apply = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply",
            json={
                "draft_id": source_patch_draft_id,
                "reviewer": "api_review_operator",
                "confirmed_manual_review": False,
            },
        )
        source_patch_apply = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply",
            json={
                "draft_id": source_patch_draft_id,
                "reviewer": "api_review_operator",
                "notes": ["Applied into draft source manifest for API test."],
                "evidence_refs": ["official:/v2/achievements?source-edit-patch-apply"],
                "confirmed_manual_review": True,
            },
        )
        source_patch_apply_audit = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply-audit?reviewer=api_review_operator"
        )
        source_patch_apply_audit_markdown = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply-audit?format=markdown"
        )
        source_patch_apply_audit_csv = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply-audit?format=csv"
        )
        draft_source_id = source_patch_apply.json()["data"]["source_edit_patch_apply"]["output_source_id"]
        blocked_draft_promotion = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/promote-draft-source",
            json={
                "draft_source_id": draft_source_id,
                "reviewer": "api_review_operator",
                "confirmed_reviewed": False,
            },
        )
        draft_promotion = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/promote-draft-source",
            json={
                "draft_source_id": draft_source_id,
                "reviewer": "api_review_operator",
                "review_notes": ["Promoted API draft source manifest after patch apply review."],
                "evidence_refs": ["official:/v2/achievements?draft-source-promotion"],
                "overwrite_existing": True,
                "confirmed_reviewed": True,
            },
        )
        draft_promotion_audit = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/promote-draft-source-audit?reviewer=api_review_operator"
        )
        draft_promotion_audit_markdown = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/promote-draft-source-audit?format=markdown"
        )
        draft_promotion_audit_csv = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/promote-draft-source-audit?format=csv"
        )
        release_evidence_bundle = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle")
        release_evidence_bundle_markdown = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle?format=markdown")
        release_evidence_bundle_csv = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle?format=csv")
        release_evidence_bundle_manifest = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle?format=manifest")
        release_evidence_archive = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive?archived_by=api_review_operator&retention_policy=retain_365_days"
        )
        release_evidence_archive_second = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive?archived_by=api_review_operator&retention_policy=retain_365_days"
        )
        release_evidence_archive_index = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive?archived_by=api_review_operator"
        )
        release_evidence_archive_markdown = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive?format=markdown"
        )
        release_evidence_archive_csv = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive?format=csv"
        )
        release_evidence_archive_diff = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive/diff"
        )
        release_evidence_archive_diff_markdown = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive/diff?format=markdown"
        )
        release_evidence_archive_diff_csv = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive/diff?format=csv"
        )
        blocked_release_signoff = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/signoff",
            json={
                "reviewer": "api_review_operator",
                "notes": ["Blocked unconfirmed sign-off."],
                "confirmed_signoff": False,
            },
        )
        release_signoff = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/signoff",
            json={
                "reviewer": "api_review_operator",
                "notes": ["Release evidence archive and diff reviewed."],
                "evidence_refs": ["api-test:release-signoff"],
                "confirmed_signoff": True,
            },
        )
        release_signoff_audit = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/signoff-audit?reviewer=api_review_operator"
        )
        release_signoff_audit_markdown = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/signoff-audit?format=markdown"
        )
        release_signoff_audit_csv = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/signoff-audit?format=csv"
        )
        release_dashboard = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-dashboard")
        release_dashboard_markdown = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-dashboard?format=markdown")
        release_dashboard_csv = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-dashboard?format=csv")
        release_export_packet = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet")
        release_export_packet_markdown = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet?format=markdown")
        release_export_packet_csv = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet?format=csv")
        release_export_packet_manifest = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet?format=manifest")
        release_export_artifacts = client.post("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts")
        release_export_artifact_index = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts")
        release_export_bundle_manifest = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle?format=manifest"
        )
        release_export_bundle_zip = client.get("/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle")
        release_export_bundle_verify_current = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verify"
        )
        release_export_bundle_audit_record = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verification-audit",
            json={
                "reviewer": "promotion_api_release_bundle",
                "notes": ["API test recorded release bundle verification audit."],
            },
        )

        assert blocked_review.status_code == 400
        assert review_action.status_code == 200
        assert review_action.json()["data"]["remediation_review"]["item_id"] == remediation_item_id
        assert review_action.json()["data"]["remediation_review"]["status"] == "acknowledged"
        assert review_audit.status_code == 200
        assert review_audit.json()["data"]["remediation_review_audit"]["records"][0]["reviewer"] == "api_review_operator"
        assert "# Achievement Route Remediation Review Audit" in review_audit_markdown.text
        assert "event_id,occurred_at,reviewer,status" in review_audit_csv.text
        assert remediation_readiness.status_code == 200
        assert remediation_readiness.json()["data"]["remediation_readiness"]["open_p0_count"] >= 1
        assert "# Achievement Route Remediation Readiness" in remediation_readiness_markdown.text
        assert "ready,maturity_label,readiness_score" in remediation_readiness_csv.text
        assert action_bundle.status_code == 200
        assert action_bundle.json()["data"]["operator_action_bundle"]["remediation_queue"]["open_item_count"] >= 1
        assert action_bundle_review.status_code == 200
        assert action_bundle_review.json()["data"]["operator_action_bundle"]["remediation_review"]["status"] == "resolved"
        assert "# Achievement Route Operator Action Bundle" in action_bundle_markdown.text
        assert "quality_maturity,quality_score,queue_item_count" in action_bundle_csv.text
        assert release_packet.status_code == 200
        assert release_packet.json()["data"]["operator_release_packet"]["manifest"]["packet_schema"] == "gw2radar.achievement_route_operator_release_packet.v1"
        assert "# Achievement Route Operator Release Packet" in release_packet_markdown.text
        assert "packet_id,ready,maturity_label" in release_packet_csv.text
        assert release_packet_manifest.json()["packet_schema"] == "gw2radar.achievement_route_operator_release_packet.v1"
        assert backfill_candidates.status_code == 200
        assert backfill_candidates.json()["data"]["backfill_candidates"]["candidate_count"] >= 1
        assert "# Achievement Route Backfill Candidates" in backfill_candidates_markdown.text
        assert "candidate_id,item_id,priority" in backfill_candidates_csv.text
        assert blocked_backfill_review.status_code == 400
        assert backfill_review.status_code == 200
        assert backfill_review.json()["data"]["backfill_candidate_review"]["candidate_id"] == backfill_candidate_id
        assert backfill_review.json()["data"]["backfill_candidate_review"]["status"] == "acknowledged"
        assert backfill_audit.status_code == 200
        assert backfill_audit.json()["data"]["backfill_candidate_review_audit"]["records"][0]["candidate_id"] == backfill_candidate_id
        assert "# Achievement Route Backfill Candidate Review Audit" in backfill_audit_markdown.text
        assert "candidate_id,item_id" in backfill_audit_csv.text
        assert backfill_readiness.status_code == 200
        assert backfill_readiness.json()["data"]["backfill_candidate_readiness"]["open_candidate_count"] >= 1
        assert "# Achievement Route Backfill Candidate Readiness" in backfill_readiness_markdown.text
        assert "ready,maturity_label,readiness_score" in backfill_readiness_csv.text
        assert backfill_resolved_review.status_code == 200
        assert backfill_resolved_review.json()["data"]["backfill_candidate_review"]["status"] == "resolved"
        assert source_patch_draft.status_code == 200
        assert source_patch_draft.json()["data"]["source_edit_patch_draft"]["draft_count"] >= 1
        assert source_patch_draft.json()["data"]["source_edit_patch_draft"]["operation_count"] >= 1
        assert "# Achievement Route Source Edit Patch Draft" in source_patch_draft_markdown.text
        assert "draft_id,candidate_id,item_id" in source_patch_draft_csv.text
        assert blocked_patch_apply.status_code == 400
        assert source_patch_apply.status_code == 200
        assert source_patch_apply.json()["data"]["source_edit_patch_apply"]["draft_id"] == source_patch_draft_id
        assert source_patch_apply.json()["data"]["source_edit_patch_apply"]["output_manifest_path"]
        assert source_patch_apply_audit.status_code == 200
        assert source_patch_apply_audit.json()["data"]["source_edit_patch_apply_audit"]["records"][0]["draft_id"] == source_patch_draft_id
        assert "# Achievement Route Source Edit Patch Apply Audit" in source_patch_apply_audit_markdown.text
        assert "event_id,applied_at,reviewer,draft_id" in source_patch_apply_audit_csv.text
        assert blocked_draft_promotion.status_code == 400
        assert draft_promotion.status_code == 200
        assert draft_promotion.json()["data"]["draft_source_promotion"]["draft_source_id"] == draft_source_id
        assert draft_promotion.json()["data"]["draft_source_promotion"]["planner_ingestion_status"] == "ready"
        assert draft_promotion_audit.status_code == 200
        assert draft_promotion_audit.json()["data"]["draft_source_promotion_audit"]["records"][0]["draft_source_id"] == draft_source_id
        assert "# Achievement Route Draft Source Promotion Audit" in draft_promotion_audit_markdown.text
        assert "event_id,promoted_at,reviewer,draft_source_id" in draft_promotion_audit_csv.text
        assert release_evidence_bundle.status_code == 200
        assert release_evidence_bundle.json()["data"]["release_evidence_bundle"]["official_promotion_audit_count"] >= 1
        assert release_evidence_bundle.json()["data"]["release_evidence_bundle"]["patch_apply_audit_count"] >= 1
        assert release_evidence_bundle.json()["data"]["release_evidence_bundle"]["draft_source_promotion_audit_count"] >= 1
        assert "# Achievement Route Unified Release Evidence Bundle" in release_evidence_bundle_markdown.text
        assert "bundle_id,ready,maturity_label" in release_evidence_bundle_csv.text
        assert release_evidence_bundle_manifest.json()["bundle_schema"] == "gw2radar.achievement_route_unified_release_evidence_bundle.v1"
        assert release_evidence_archive.status_code == 200
        assert release_evidence_archive.json()["data"]["release_evidence_archive"]["archived_by"] == "api_review_operator"
        assert len(release_evidence_archive.json()["data"]["release_evidence_archive"]["checksum_sha256"]) == 64
        assert release_evidence_archive_second.status_code == 200
        assert release_evidence_archive_index.status_code == 200
        assert release_evidence_archive_index.json()["data"]["release_evidence_archive_index"]["total_records"] == 2
        assert "# Achievement Route Release Evidence Archive" in release_evidence_archive_markdown.text
        assert "archive_id,bundle_id,archived_at" in release_evidence_archive_csv.text
        assert release_evidence_archive_diff.status_code == 200
        assert release_evidence_archive_diff.json()["data"]["release_evidence_archive_diff"]["regression_count"] == 0
        assert release_evidence_archive_diff.json()["data"]["release_evidence_archive_diff"]["checksum_changed"] is True
        assert "# Achievement Route Release Evidence Archive Diff" in release_evidence_archive_diff_markdown.text
        assert "baseline_archive_id,candidate_archive_id,ready" in release_evidence_archive_diff_csv.text
        assert blocked_release_signoff.status_code == 400
        assert release_signoff.status_code == 200
        assert release_signoff.json()["data"]["release_signoff"]["reviewer"] == "api_review_operator"
        assert release_signoff.json()["data"]["release_signoff"]["regression_count"] == 0
        assert release_signoff_audit.status_code == 200
        assert release_signoff_audit.json()["data"]["release_signoff_audit"]["records"][0]["reviewer"] == "api_review_operator"
        assert "# Achievement Route Release Sign-off Audit" in release_signoff_audit_markdown.text
        assert "signoff_id,signed_off_at,reviewer,status" in release_signoff_audit_csv.text
        assert release_dashboard.status_code == 200
        assert release_dashboard.json()["data"]["operator_release_dashboard"]["archive_count"] == 2
        assert release_dashboard.json()["data"]["operator_release_dashboard"]["diff_regression_count"] == 0
        assert release_dashboard.json()["data"]["operator_release_dashboard"]["latest_signoff_reviewer"] == "api_review_operator"
        assert "# Achievement Route Operator Release Dashboard" in release_dashboard_markdown.text
        assert "ready,maturity_label,bundle_id" in release_dashboard_csv.text
        assert release_export_packet.status_code == 200
        assert release_export_packet.json()["data"]["release_export_packet"]["artifact_count"] >= 8
        assert release_export_packet.json()["data"]["release_export_packet"]["latest_signoff_status"] in {"signed_off", "blocked"}
        assert "# Achievement Route Release Export Packet" in release_export_packet_markdown.text
        assert "packet_id,ready,maturity_label" in release_export_packet_csv.text
        assert release_export_packet_manifest.json()["packet_schema"] == "gw2radar.achievement_route_release_export_packet.v1"
        assert release_export_artifacts.status_code == 200
        assert release_export_artifacts.json()["data"]["release_export_artifacts"]["file_count"] == 3
        first_artifact_path = release_export_artifacts.json()["data"]["release_export_artifacts"]["files"][0]["relative_path"]
        release_export_artifact_file = client.get(
            f"/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/{first_artifact_path}"
        )
        assert release_export_artifact_index.status_code == 200
        assert release_export_artifact_index.json()["data"]["release_export_artifacts"]["file_count"] == 3
        assert release_export_artifact_file.status_code == 200
        assert "secret-key" not in release_export_artifact_file.text.lower()
        assert release_export_bundle_manifest.status_code == 200
        assert release_export_bundle_manifest.json()["data"]["release_export_bundle"]["file_count"] == 4
        assert release_export_bundle_zip.status_code == 200
        assert release_export_bundle_zip.headers["content-type"] == "application/zip"
        assert release_export_bundle_zip.headers["x-checksum-sha256"]
        assert set(ZipFile(BytesIO(release_export_bundle_zip.content)).namelist()) == {
            "achievement_route_release_export/artifact_index.json",
            "achievement_route_release_export/release_export_packet_manifest.json",
            "achievement_route_release_export/release_export_packet.md",
            "achievement_route_release_export/release_export_packet.csv",
        }
        release_export_bundle_verify_upload = client.post(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verify",
            content=release_export_bundle_zip.content,
            headers={"content-type": "application/zip"},
        )
        release_export_bundle_audit = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verification-audit?reviewer=promotion_api_release_bundle"
        )
        release_export_bundle_audit_markdown = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verification-audit?format=markdown"
        )
        release_export_bundle_audit_csv = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verification-audit?format=csv"
        )
        operator_handoff = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/handoff-checklist"
        )
        operator_handoff_markdown = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/handoff-checklist?format=markdown"
        )
        operator_handoff_csv = client.get(
            "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/handoff-checklist?format=csv"
        )
        assert release_export_bundle_verify_current.status_code == 200
        assert release_export_bundle_verify_current.json()["data"]["release_export_bundle_verification"]["ready"] is True
        assert release_export_bundle_verify_upload.status_code == 200
        assert release_export_bundle_verify_upload.json()["data"]["release_export_bundle_verification"]["ready"] is True
        assert release_export_bundle_audit_record.status_code == 200
        assert release_export_bundle_audit_record.json()["data"]["release_export_bundle_verification_audit_record"]["ready"] is True
        assert release_export_bundle_audit.status_code == 200
        assert release_export_bundle_audit.json()["data"]["release_export_bundle_verification_audit"]["records"][0]["reviewer"] == "promotion_api_release_bundle"
        assert release_export_bundle_audit_markdown.status_code == 200
        assert "Achievement Route Release Bundle Verification Audit" in release_export_bundle_audit_markdown.text
        assert release_export_bundle_audit_csv.status_code == 200
        assert "audit_id,verified_at,reviewer,ready,checksum_sha256" in release_export_bundle_audit_csv.text
        assert operator_handoff.status_code == 200
        assert operator_handoff.json()["data"]["operator_handoff_checklist"]["ready"] is True
        assert operator_handoff.json()["data"]["operator_handoff_checklist"]["maturity_label"] == "ready"
        assert operator_handoff_markdown.status_code == 200
        assert "Achievement Route Operator Handoff Checklist" in operator_handoff_markdown.text
        assert operator_handoff_csv.status_code == 200
        assert "ready,maturity_label,packet_id,packet_artifact_count" in operator_handoff_csv.text
        assert "secret-key" not in release_export_bundle_zip.content.decode("latin1").lower()
    finally:
        achievement_route_routes.gateway_factory = original_factory
        achievement_route_routes.source_root = original_source_root
        achievement_route_routes.audit_root = original_audit_root
        achievement_route_routes.release_export_root = original_release_export_root
        rmtree(temp_root, ignore_errors=True)
        rmtree(audit_root, ignore_errors=True)
        rmtree(release_export_root, ignore_errors=True)


def _official_preview_request() -> OfficialAchievementRoutePreviewRequest:
    return OfficialAchievementRoutePreviewRequest(
        source_id="official:achievement-route-preview:test",
        title="Unit official achievement preview",
        goal_id="aurora_sample",
        reviewed_by="unit_test_operator",
        achievement_details=[
            {
                "id": 1001,
                "name": "Bloodstone Fen Sample Collection",
                "description": "Complete a collection step in Bloodstone Fen.",
                "requirement": "Finish the Bloodstone Fen collection check.",
                "bits": [{"type": "Text", "text": "Sample bit"}],
            },
            {
                "id": 1002,
                "name": "Daily Ember Bay Sample",
                "description": "Complete a daily checkpoint in Ember Bay.",
                "requirement": "Daily Ember Bay route review.",
                "flags": ["Daily"],
            },
            {
                "id": 1003,
                "name": "Fractal Sample Collection",
                "description": "Complete a Fractal collection step with a group.",
                "requirement": "Finish a Fractal route checkpoint.",
            },
        ],
        account_achievements=[
            {"id": 1001, "current": 1, "max": 3},
            {"id": 1002, "current": 1, "max": 1},
        ],
    )


def _official_fetch_request() -> OfficialAchievementFetchPreviewRequest:
    return OfficialAchievementFetchPreviewRequest(
        source_id="official:achievement-route-fetch-preview:test",
        title="Unit official fetch preview",
        goal_id="aurora_sample",
        reviewed_by="unit_test_operator",
        achievement_ids=[1001, 1002, 404],
        account_achievements=[
            {"id": 1001, "current": 1, "max": 3},
            {"id": 1002, "current": 1, "max": 1},
        ],
    )


class FetchPreviewGateway:
    def __init__(self) -> None:
        self.batch_calls: list[tuple[str, list[int | str]]] = []

    def get_batch(self, endpoint, *, ids, params=None, api_key=None, priority="P3"):
        self.batch_calls.append((endpoint, list(ids)))
        payload = [
            {
                "id": 1001,
                "name": "Bloodstone Fen Gateway Collection",
                "description": "Complete a collection step in Bloodstone Fen.",
                "requirement": "Finish the Bloodstone Fen gateway route check.",
            },
            {
                "id": 1002,
                "name": "Daily Ember Bay Gateway",
                "description": "Complete a daily checkpoint in Ember Bay.",
                "requirement": "Daily Ember Bay gateway route review.",
                "flags": ["Daily"],
            },
        ]
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id="fetch-preview:test",
            payload=payload,
            evidence_id="evidence:fetch-preview",
        )

    def get(self, endpoint, *, params=None, api_key=None, priority="P3"):
        return GatewayResult(
            status=GatewayStatus.OK,
            endpoint=endpoint,
            request_id="fetch-preview:account",
            payload=[{"id": 1002, "current": 1, "max": 1}],
            evidence_id="evidence:account-achievements",
        )


def _temp_source_root(prefix: str) -> Path:
    path = Path(".test_tmp") / f"achievement-route-{prefix}-{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path
