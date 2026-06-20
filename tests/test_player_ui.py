from pathlib import Path

from fastapi.testclient import TestClient

from gw2radar.api.main import app


client = TestClient(app)


def test_player_ui_page_serves_player_workbench() -> None:
    response = client.get("/player")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "GW2Radar Player Dashboard" in response.text
    assert "Welcome to GW2Radar" in response.text
    assert "Returner Diagnosis" in response.text
    assert "Readiness score" in response.text
    assert "Legendary Planner Pro" in response.text
    assert "Build Fit Advisor" in response.text
    assert "Character snapshot" in response.text
    assert "Load character snapshots" in response.text
    assert "Upgrade evidence rules" in response.text
    assert "Preview upgrade pack" in response.text
    assert "Import disabled rules" in response.text
    assert "Enable selected rule" in response.text
    assert "Data Freshness" in response.text
    assert "Privacy & Safety" in response.text
    assert "No gameplay automation" in response.text
    assert "Workflow readiness" in response.text
    assert "No dashboard summary yet." in response.text
    assert "Delete all private data" in response.text
    assert "Check permissions" in response.text
    assert "Sync now" in response.text
    assert "Permission status not checked." in response.text
    assert "Run connection diagnostic" in response.text
    assert "Export debug bundle" in response.text
    assert "Build Fit bridge status" in response.text
    assert "Today / this week" in response.text
    assert "Generate full report" in response.text
    assert "Mock returner checkout" in response.text
    assert "Refresh freshness to load recommendation-level source confidence." in response.text
    assert "Operator review gate" in response.text
    assert "Official achievement ids" in response.text
    assert "Fetch preview" in response.text
    assert "Promote reviewed" in response.text
    assert "Verify promoted plan" in response.text
    assert "Load audit" in response.text
    assert "Export audit CSV" in response.text
    assert "Audit records" in response.text
    assert "Release readiness" in response.text
    assert "Export readiness CSV" in response.text
    assert "Source quality" in response.text
    assert "Export quality CSV" in response.text
    assert "Quality" in response.text
    assert "Remediation queue" in response.text
    assert "Export remediation CSV" in response.text
    assert "Remediation" in response.text
    assert "Remediation status" in response.text
    assert "Review selected remediation" in response.text
    assert "Load remediation audit" in response.text
    assert "Export remediation audit CSV" in response.text
    assert "Remediation readiness" in response.text
    assert "Export remediation readiness CSV" in response.text
    assert "Remediation gate" in response.text
    assert "Action bundle" in response.text
    assert "Review via bundle" in response.text
    assert "Release packet" in response.text
    assert "Export release packet CSV" in response.text
    assert "Export packet manifest" in response.text
    assert "Backfill candidates" in response.text
    assert "Export backfill CSV" in response.text
    assert "Review backfill candidate" in response.text
    assert "Load backfill audit" in response.text
    assert "Export backfill audit CSV" in response.text
    assert "Backfill readiness" in response.text
    assert "Export backfill readiness CSV" in response.text
    assert "Backfill gate" in response.text
    assert "Source patch draft" in response.text
    assert "Export source patch CSV" in response.text
    assert "Apply source patch draft" in response.text
    assert "Load source patch audit" in response.text
    assert "Export source patch audit CSV" in response.text
    assert "Promote draft source" in response.text
    assert "Load draft promotion audit" in response.text
    assert "Export draft promotion CSV" in response.text
    assert "Draft promotion" in response.text
    assert "Release evidence bundle" in response.text
    assert "Export evidence CSV" in response.text
    assert "Export evidence manifest" in response.text
    assert "Archive evidence" in response.text
    assert "Load evidence archive" in response.text
    assert "Export archive CSV" in response.text
    assert "Review archive diff" in response.text
    assert "Export diff CSV" in response.text
    assert "Sign off release" in response.text
    assert "Load sign-off audit" in response.text
    assert "Export sign-off CSV" in response.text
    assert "Evidence bundle" in response.text
    assert "Evidence archive" in response.text
    assert "Archive diff" in response.text
    assert "Release sign-off" in response.text


def test_player_ui_static_assets_are_served() -> None:
    css = client.get("/player-ui/styles.css")
    js = client.get("/player-ui/app.js")

    assert css.status_code == 200
    assert ".app-shell" in css.text
    assert ".dashboard-grid" in css.text
    assert js.status_code == 200
    assert "/api/v1/legendary/recompute" in js.text
    assert "/api/v1/builds/transition-plan" in js.text
    assert "/api/v1/builds/character-snapshots" in js.text
    assert "/api/v1/kb/rule-packs/build_upgrade_effects" in js.text
    assert "/api/v1/kb/rules?domain=build&name_contains=Build%20upgrade" in js.text
    assert "enableBuildUpgradeRule" in js.text
    assert "confirmed_reviewed" in js.text
    assert "applyAccountGearSnapshot" in js.text
    assert "/account/api-key" in js.text
    assert "/account/api-key/permissions" in js.text
    assert "/account/diagnostic" in js.text
    assert "/account/debug-bundle" in js.text
    assert "/api/v1/player/dashboard" in js.text
    assert "/api/v1/player/freshness-annotations" in js.text
    assert "/api/v1/legendary/goals/catalog" in js.text
    assert "/api/v1/legendary/actions" in js.text
    assert "/api/v1/returner/report" in js.text
    assert "plan_returner_once" in js.text
    assert "renderPermissionReport" in js.text
    assert "renderConnectionDiagnostic" in js.text
    assert "runDiagnosticFix" in js.text
    assert "diagnosticDetailsText" in js.text
    assert "debugBundleClientState" in js.text
    assert "downloadJson" in js.text
    assert "focus_api_key_input" in js.text
    assert "renderSyncProgress" in js.text
    assert "renderFreshnessAnnotations" in js.text
    assert "gw2radar.api_key_permissions.v1" in js.text
    assert "gw2radar.account_connection_diagnostic.v1" in js.text
    assert "gw2radar.player.activeView" in js.text
    assert "summarizeResult" in js.text
    assert "artifactPath.split" in js.text
    assert "Import or select a build before running this action." in js.text
    assert "gw2radar.player.intent" in js.text
    assert "gw2radar.player.reportHistory" in js.text
    assert "/api/v1/security/private-data" in js.text
    assert "refreshFreshness" in js.text
    assert "/api/v1/returner/readiness" in js.text
    assert "updateReturnerScores" in js.text
    assert "rune/sigil/relic effect checks" in js.text
    assert "payload?.is_configured" in js.text
    assert "Sync now queues one account snapshot job" in js.text
    assert "/api/v1/account/sync/drain-one" in js.text
    assert "/api/v1/achievement-routes/official-fetch-preview" in js.text
    assert "/api/v1/achievement-routes/official-fetch-preview/promote-reviewed" in js.text
    assert "fetchOfficialAchievementRoutePreview" in js.text
    assert "promoteOfficialAchievementRouteReviewed" in js.text
    assert "verifyPromotedAchievementRoute" in js.text
    assert "loadAchievementRoutePromotionAudit" in js.text
    assert "exportAchievementRoutePromotionAudit" in js.text
    assert "loadAchievementRouteReleaseReadiness" in js.text
    assert "exportAchievementRouteReleaseReadiness" in js.text
    assert "loadAchievementRouteSourceQuality" in js.text
    assert "exportAchievementRouteSourceQuality" in js.text
    assert "loadAchievementRouteRemediationQueue" in js.text
    assert "exportAchievementRouteRemediationQueue" in js.text
    assert "reviewAchievementRouteRemediation" in js.text
    assert "loadAchievementRouteRemediationReviewAudit" in js.text
    assert "exportAchievementRouteRemediationReviewAudit" in js.text
    assert "loadAchievementRouteRemediationReadiness" in js.text
    assert "exportAchievementRouteRemediationReadiness" in js.text
    assert "loadAchievementRouteOperatorActionBundle" in js.text
    assert "reviewAchievementRouteRemediationViaBundle" in js.text
    assert "loadAchievementRouteOperatorReleasePacket" in js.text
    assert "exportAchievementRouteOperatorReleasePacket" in js.text
    assert "exportAchievementRouteOperatorReleasePacketManifest" in js.text
    assert "loadAchievementRouteBackfillCandidates" in js.text
    assert "exportAchievementRouteBackfillCandidates" in js.text
    assert "reviewAchievementRouteBackfillCandidate" in js.text
    assert "loadAchievementRouteBackfillCandidateReviewAudit" in js.text
    assert "exportAchievementRouteBackfillCandidateReviewAudit" in js.text
    assert "loadAchievementRouteBackfillCandidateReadiness" in js.text
    assert "exportAchievementRouteBackfillCandidateReadiness" in js.text
    assert "loadAchievementRouteSourceEditPatchDraft" in js.text
    assert "exportAchievementRouteSourceEditPatchDraft" in js.text
    assert "applyAchievementRouteSourceEditPatchDraft" in js.text
    assert "loadAchievementRouteSourceEditPatchApplyAudit" in js.text
    assert "exportAchievementRouteSourceEditPatchApplyAudit" in js.text
    assert "promoteAchievementRouteDraftSource" in js.text
    assert "loadAchievementRouteDraftSourcePromotionAudit" in js.text
    assert "exportAchievementRouteDraftSourcePromotionAudit" in js.text
    assert "loadAchievementRouteReleaseEvidenceBundle" in js.text
    assert "exportAchievementRouteReleaseEvidenceBundle" in js.text
    assert "exportAchievementRouteReleaseEvidenceBundleManifest" in js.text
    assert "archiveAchievementRouteReleaseEvidenceBundle" in js.text
    assert "loadAchievementRouteReleaseEvidenceArchive" in js.text
    assert "exportAchievementRouteReleaseEvidenceArchive" in js.text
    assert "reviewAchievementRouteReleaseEvidenceArchiveDiff" in js.text
    assert "exportAchievementRouteReleaseEvidenceArchiveDiff" in js.text
    assert "signoffAchievementRouteRelease" in js.text
    assert "loadAchievementRouteReleaseSignoffAudit" in js.text
    assert "exportAchievementRouteReleaseSignoffAudit" in js.text
    assert "confirmed_manual_review" in js.text
    assert "routeOfficialFetchPreviewPayload" in js.text
    assert "routeReviewPayload" in js.text
    assert "/api/v1/achievement-routes/promotion-audit" in js.text
    assert "/api/v1/achievement-routes/release-readiness" in js.text
    assert "/api/v1/achievement-routes/source-quality" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/review" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/review-audit" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/readiness" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/action-bundle" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-packet" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/review" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/review-audit" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/readiness" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/apply-audit" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/promote-draft-source" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/backfill-candidates/source-edit-patch-draft/promote-draft-source-audit" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/archive/diff" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/signoff" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-evidence-bundle/signoff-audit" in js.text


def test_player_ui_styles_cover_workflow_and_summaries() -> None:
    css = client.get("/player-ui/styles.css")

    assert css.status_code == 200
    assert ".workflow-rail" in css.text
    assert ".workflow-step.ready" in css.text
    assert ".result-summary" in css.text
    assert ".readiness-grid" in css.text
    assert ".score-card" in css.text
    assert ".gear-summary" in css.text
    assert ".rule-pack-status" in css.text
    assert ".compact-fields" in css.text
    assert ".goal-choice-grid" in css.text
    assert ".permission-grid" in css.text
    assert ".permission-status-grid" in css.text
    assert ".diagnostic-grid" in css.text
    assert ".diagnostic-check.pass" in css.text
    assert ".diagnostic-fix" in css.text
    assert ".permission-status.ready" in css.text
    assert ".freshness-annotation-grid" in css.text
    assert ".sync-checklist span.blocked" in css.text
    assert ".sync-checklist" in css.text


def test_player_ui_docs_cover_required_flows() -> None:
    docs_root = Path("docs/ui")
    required = [
        "PLAYER_UI_GUIDE.md",
        "UI_INFORMATION_ARCHITECTURE.md",
        "RETURNER_DIAGNOSIS_UI_FLOW.md",
        "LEGENDARY_PLANNER_UI_FLOW.md",
        "BUILD_FIT_UI_FLOW.md",
        "REPORT_CENTER_UI_FLOW.md",
        "PRIVACY_SAFETY_UI_FLOW.md",
        "PLAYER_UI_SEMANTIC_GRAPH_AUDIT.md",
    ]

    combined = "\n".join((docs_root / name).read_text(encoding="utf-8") for name in required)

    assert "Returner Diagnosis" in combined
    assert "Legendary Planner Pro" in combined
    assert "Build Fit Advisor" in combined
    assert "No automatic trading" in combined
    assert "API key" in combined
    assert "python -m uvicorn gw2radar.api.main:app --reload" in combined
    assert "gw2radar.player.activeBuildId" in combined
    assert "PlayerIntent" in combined
    assert "FreshnessSignal" in combined
    assert "build_upgrade_effects" in combined
    assert "reviewed and enabled KB rules" in combined
    assert "Delete all private data" in combined
    assert "Run connection diagnostic" in combined
    assert "Export debug bundle" in combined
    assert "promote-reviewed" in combined
