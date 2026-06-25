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
    assert "Player OS Intent Builder" in response.text
    assert "Build Player OS plan" in response.text
    assert "What should I do now?" in response.text
    assert "Open templates" in response.text
    assert "Player OS Plan" in response.text
    assert "Revise with 30m/day" in response.text
    assert "What-if budget 100g" in response.text
    assert "Open full Player OS" in response.text
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
    assert "Check readiness" in response.text
    assert "Explain empty results" in response.text
    assert "Refresh status to see why account-aware results may still be empty." in response.text
    assert "Player Readiness" in response.text
    assert "Run Check readiness to inspect the full player path." in response.text
    assert "Export readiness MD" in response.text
    assert "Export readiness CSV" in response.text
    assert "Save readiness snapshot" in response.text
    assert "Load readiness history" in response.text
    assert "Export history MD" in response.text
    assert "Export history CSV" in response.text
    assert "Load history correlation" in response.text
    assert "Export correlation MD" in response.text
    assert "Export correlation CSV" in response.text
    assert "Load session packet" in response.text
    assert "Export packet MD" in response.text
    assert "Export packet CSV" in response.text
    assert "Write packet files" in response.text
    assert "Load packet files" in response.text
    assert "Create support handoff" in response.text
    assert "Write handoff files" in response.text
    assert "Load handoff files" in response.text
    assert "Download handoff zip" in response.text
    assert "Verify handoff zip" in response.text
    assert "Record zip audit" in response.text
    assert "Load zip audit" in response.text
    assert "Load handoff readiness" in response.text
    assert "Load operator packet" in response.text
    assert "Load support dashboard" in response.text
    assert "Write final archive" in response.text
    assert "Download final archive" in response.text
    assert "Verify final archive" in response.text
    assert "Session Packet" in response.text
    assert "Load session packet to prepare a debug-safe support summary." in response.text
    assert "Write packet files to create a checksum manifest for support handoff." in response.text
    assert "Create support handoff after connection diagnostic and packet files are ready." in response.text
    assert "Write handoff files to archive the support bundle manifest and checksum." in response.text
    assert "Download or verify a read-only handoff zip after handoff files are written." in response.text
    assert "Record zip audit after verification to preserve support handoff evidence." in response.text
    assert "Load handoff readiness to confirm support transfer gates." in response.text
    assert "Load operator packet to review the support runbook and transfer files." in response.text
    assert "Load support dashboard to inspect all handoff gates in one view." in response.text
    assert "Write final archive to package support dashboard, operator packet, readiness checklist, and audit exports." in response.text
    assert "History Correlation" in response.text
    assert "Load history correlation after saving readiness and value snapshots." in response.text
    assert "Readiness history" in response.text
    assert "Save two readiness snapshots to compare sync and price-refresh changes." in response.text
    assert "Account Value Coverage" in response.text
    assert "Location breakdown" in response.text
    assert "Status breakdown" in response.text
    assert "Source diagnostics" in response.text
    assert "Next value actions" in response.text
    assert "Top Holdings" in response.text
    assert "Value Warnings" in response.text
    assert "Refresh official prices" in response.text
    assert "Refresh status to inspect missing or stale price coverage." in response.text
    assert "Legendary value evidence" in response.text
    assert "Market value evidence" in response.text
    assert "Build value evidence" in response.text
    assert "Run cheap/fast path to inspect account value evidence." in response.text
    assert "Load market signals to inspect account value evidence." in response.text
    assert "Run fit score or transition plan to inspect account value evidence." in response.text
    assert "Export value MD" in response.text
    assert "Export value CSV" in response.text
    assert "Save value snapshot" in response.text
    assert "Load value history" in response.text
    assert "Export value history MD" in response.text
    assert "Export value history CSV" in response.text
    assert "Value history" in response.text
    assert "Save two value snapshots to compare sync and price-refresh changes." in response.text
    assert "Delete all private data" in response.text
    assert "Check permissions" in response.text
    assert "Sync now" in response.text
    assert "Run sync worker" in response.text
    assert "Queue health" in response.text
    assert "Load queue health to inspect worker depth, retry state, and latest job diagnostics." in response.text
    assert "Shared inventory" in response.text
    assert "TP buys" in response.text
    assert "TP sells" in response.text
    assert "Permission status not checked." in response.text
    assert "Run connection diagnostic" in response.text
    assert "Export debug bundle" in response.text
    assert "Build Fit bridge status" in response.text
    assert "Today / this week" in response.text
    assert "Generate full report" in response.text
    assert "Mock returner checkout" in response.text
    assert "Refresh freshness to load recommendation-level source confidence." in response.text
    assert "Public refresh health" in response.text
    assert "Load public refresh health to inspect retry/backoff state for public facts." in response.text
    assert "Gateway timeline" in response.text
    assert "Gateway Incident Timeline" in response.text
    assert "Load gateway timeline to correlate account sync, public refresh, and market price refresh events." in response.text
    assert "Save gateway snapshot" in response.text
    assert "Gateway history" in response.text
    assert "Export gateway MD" in response.text
    assert "Export gateway CSV" in response.text
    assert "Save two gateway snapshots to compare retry and failure changes across sessions." in response.text
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
    assert "Release dashboard" in response.text
    assert "Export dashboard CSV" in response.text
    assert "Release export packet" in response.text
    assert "Export packet CSV" in response.text
    assert "Export packet manifest" in response.text
    assert "Write packet files" in response.text
    assert "Load packet files" in response.text
    assert "Open packet file" in response.text
    assert "Bundle manifest" in response.text
    assert "Download bundle" in response.text
    assert "Verify bundle" in response.text
    assert "Record bundle audit" in response.text
    assert "Load bundle audit" in response.text
    assert "Export bundle audit CSV" in response.text
    assert "Handoff checklist" in response.text
    assert "Export handoff CSV" in response.text
    assert "Release notes" in response.text
    assert "Export notes CSV" in response.text
    assert "Operator runbook" in response.text
    assert "Export runbook CSV" in response.text
    assert "Final dashboard" in response.text
    assert "Export final dashboard CSV" in response.text
    assert "Final maturity audit" in response.text
    assert "Export maturity CSV" in response.text
    assert "Evidence bundle" in response.text
    assert "Evidence archive" in response.text
    assert "Archive diff" in response.text
    assert "Release sign-off" in response.text
    assert "Release dashboard" in response.text
    assert "Export packet" in response.text
    assert "Packet files" in response.text
    assert "Packet bundle" in response.text
    assert "Bundle verify" in response.text
    assert "Bundle audit" in response.text
    assert "Handoff" in response.text
    assert "Runbook" in response.text
    assert "Maturity audit" in response.text


def test_player_ui_static_assets_are_served() -> None:
    css = client.get("/player-ui/styles.css")
    js = client.get("/player-ui/app.js")

    assert css.status_code == 200
    assert ".app-shell" in css.text
    assert ".dashboard-grid" in css.text
    assert js.status_code == 200
    assert "/api/v1/legendary/recompute" in js.text
    assert "/api/v1/intents/start" in js.text
    assert "/api/v1/now" in js.text
    assert "startPlayerOsIntent" in js.text
    assert "loadPlayerOsNow" in js.text
    assert "revisePlayerOsPlan" in js.text
    assert "whatIfPlayerOsPlan" in js.text
    assert "renderPlayerOsPlan" in js.text
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
    assert "/account/first-run-summary" in js.text
    assert "/api/v1/account/sync/health" in js.text
    assert "/api/v1/account/sync/worker/run" in js.text
    assert "firstRunSummary" in js.text
    assert "renderFirstRunSummary" in js.text
    assert "accountSyncWorkerRun" in js.text
    assert "accountSyncHealth" in js.text
    assert "renderAccountSyncHealth" in js.text
    assert "#first-run-summary" in js.text
    assert "/account/debug-bundle" in js.text
    assert "/api/v1/player/dashboard" in js.text
    assert "/api/v1/player/readiness" in js.text
    assert "playerReadiness" in js.text
    assert "exportPlayerReadinessMarkdown" in js.text
    assert "exportPlayerReadinessCsv" in js.text
    assert "/api/v1/player/readiness?format=markdown" in js.text
    assert "/api/v1/player/readiness?format=csv" in js.text
    assert "gw2radar-player-readiness.md" in js.text
    assert "gw2radar-player-readiness.csv" in js.text
    assert "savePlayerReadinessSnapshot" in js.text
    assert "loadPlayerReadinessHistory" in js.text
    assert "exportPlayerReadinessHistoryMarkdown" in js.text
    assert "exportPlayerReadinessHistoryCsv" in js.text
    assert "/api/v1/player/readiness/history?source=player_dashboard" in js.text
    assert "/api/v1/player/readiness/history?format=markdown&limit=10" in js.text
    assert "/api/v1/player/readiness/history?format=csv&limit=10" in js.text
    assert "gw2radar-player-readiness-history.md" in js.text
    assert "gw2radar-player-readiness-history.csv" in js.text
    assert "renderPlayerReadinessHistory" in js.text
    assert "loadPlayerHistoryCorrelation" in js.text
    assert "exportPlayerHistoryCorrelationMarkdown" in js.text
    assert "exportPlayerHistoryCorrelationCsv" in js.text
    assert "/api/v1/player/history/correlation?limit=10" in js.text
    assert "/api/v1/player/history/correlation?format=markdown&limit=10" in js.text
    assert "/api/v1/player/history/correlation?format=csv&limit=10" in js.text
    assert "gw2radar-player-history-correlation.md" in js.text
    assert "gw2radar-player-history-correlation.csv" in js.text
    assert "renderPlayerHistoryCorrelation" in js.text
    assert "gw2radar.player_history_correlation.v1" in js.text
    assert "loadPlayerSessionPacket" in js.text
    assert "exportPlayerSessionPacketMarkdown" in js.text
    assert "exportPlayerSessionPacketCsv" in js.text
    assert "/api/v1/player/session-packet?limit=10" in js.text
    assert "/api/v1/player/session-packet?format=markdown&limit=10" in js.text
    assert "/api/v1/player/session-packet?format=csv&limit=10" in js.text
    assert "gw2radar-player-session-packet.md" in js.text
    assert "gw2radar-player-session-packet.csv" in js.text
    assert "renderPlayerSessionPacket" in js.text
    assert "gw2radar.player_session_packet.v1" in js.text
    assert "writePlayerSessionPacketArtifacts" in js.text
    assert "loadPlayerSessionPacketArtifacts" in js.text
    assert "/api/v1/player/session-packet/artifacts?limit=10" in js.text
    assert "renderPlayerSessionPacketArtifacts" in js.text
    assert "createPlayerSupportHandoff" in js.text
    assert "/api/v1/player/support-handoff?limit=10" in js.text
    assert "renderPlayerSupportHandoff" in js.text
    assert "writePlayerSupportHandoffArtifacts" in js.text
    assert "loadPlayerSupportHandoffArtifacts" in js.text
    assert "/api/v1/player/support-handoff/artifacts?limit=10" in js.text
    assert "renderPlayerSupportHandoffArtifacts" in js.text
    assert "downloadPlayerSupportHandoffZip" in js.text
    assert "verifyPlayerSupportHandoffZip" in js.text
    assert "/api/v1/player/support-handoff/artifacts/bundle" in js.text
    assert "/api/v1/player/support-handoff/artifacts/bundle/verify" in js.text
    assert "renderPlayerSupportHandoffZipVerification" in js.text
    assert "recordPlayerSupportHandoffZipAudit" in js.text
    assert "loadPlayerSupportHandoffZipAudit" in js.text
    assert "/api/v1/player/support-handoff/artifacts/bundle/verification-audit" in js.text
    assert "renderPlayerSupportHandoffZipAudit" in js.text
    assert "loadPlayerSupportHandoffReadiness" in js.text
    assert "/api/v1/player/support-handoff/readiness-checklist" in js.text
    assert "renderPlayerSupportHandoffReadiness" in js.text
    assert "loadPlayerSupportHandoffOperatorPacket" in js.text
    assert "/api/v1/player/support-handoff/operator-packet" in js.text
    assert "renderPlayerSupportHandoffOperatorPacket" in js.text
    assert "loadPlayerSupportHandoffDashboard" in js.text
    assert "/api/v1/player/support-handoff/dashboard" in js.text
    assert "renderPlayerSupportHandoffDashboard" in js.text
    assert "writePlayerSupportHandoffFinalArchive" in js.text
    assert "downloadPlayerSupportHandoffFinalArchiveZip" in js.text
    assert "verifyPlayerSupportHandoffFinalArchiveZip" in js.text
    assert "/api/v1/player/support-handoff/final-archive" in js.text
    assert "/api/v1/player/support-handoff/final-archive/bundle" in js.text
    assert "renderPlayerSupportHandoffFinalArchive" in js.text
    assert "renderPlayerReadiness" in js.text
    assert "readinessCheckClass" in js.text
    assert "gw2radar.player_readiness_summary.v1" in js.text or "readiness_score" in js.text
    assert "/api/v1/player/account-holdings" in js.text
    assert "/api/v1/player/account-value" in js.text
    assert "renderAccountValueSummary" in js.text
    assert "renderValueBreakdown" in js.text
    assert "renderTopHoldings" in js.text
    assert "renderValueWarnings" in js.text
    assert "renderPriceRemediationSummary" in js.text
    assert "renderValueSourceInsights" in js.text
    assert "renderValueRemediationActions" in js.text
    assert "renderAccountValueEvidenceBridge" in js.text
    assert "appendCompactBridgeRow" in js.text
    assert "#legendary-value-evidence" in js.text
    assert "#market-value-evidence" in js.text
    assert "#build-value-evidence" in js.text
    assert "account_value_evidence" in js.text
    assert "valueReadinessClass" in js.text
    assert "price_coverage_percent" in js.text
    assert "remediationMessage" in js.text
    assert "refreshOfficialPrices" in js.text
    assert "/api/v1/market/snapshots/official-refresh" in js.text
    assert "Official price refresh" in js.text
    assert "exportAccountValueMarkdown" in js.text
    assert "exportAccountValueCsv" in js.text
    assert "saveAccountValueSnapshot" in js.text
    assert "loadAccountValueHistory" in js.text
    assert "exportAccountValueHistoryMarkdown" in js.text
    assert "exportAccountValueHistoryCsv" in js.text
    assert "/api/v1/player/account-value/history?source=player_dashboard" in js.text
    assert "/api/v1/player/account-value/history?format=markdown&limit=10" in js.text
    assert "/api/v1/player/account-value/history?format=csv&limit=10" in js.text
    assert "gw2radar-account-value-history.md" in js.text
    assert "gw2radar-account-value-history.csv" in js.text
    assert "renderAccountValueHistory" in js.text
    assert "downloadText" in js.text
    assert "/api/v1/player/freshness-annotations" in js.text
    assert "/api/v1/public/refresh/health" in js.text
    assert "loadPublicRefreshHealth" in js.text
    assert "renderPublicRefreshHealth" in js.text
    assert "gw2radar.public_refresh_worker_health.v1" in js.text
    assert "player_action" in js.text
    assert "/api/v1/player/gateway-incidents?limit=20" in js.text
    assert "loadGatewayIncidents" in js.text
    assert "renderGatewayIncidentTimeline" in js.text
    assert "gw2radar.gateway_incident_timeline.v1" in js.text
    assert "/api/v1/player/gateway-incidents/snapshots?source=player_dashboard" in js.text
    assert "/api/v1/player/gateway-incidents/history?limit=10" in js.text
    assert "/api/v1/player/gateway-incidents/history?format=markdown&limit=10" in js.text
    assert "/api/v1/player/gateway-incidents/history?format=csv&limit=10" in js.text
    assert "saveGatewayIncidentSnapshot" in js.text
    assert "renderGatewayIncidentHistory" in js.text
    assert "gw2radar.gateway_incident_history.v1" in js.text
    assert "gw2radar-gateway-incident-history.md" in js.text
    assert "gw2radar-gateway-incident-history.csv" in js.text
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
    assert "/v2/account/inventory" in js.text
    assert "/v2/commerce/transactions/current/buys" in js.text
    assert "/v2/commerce/transactions/current/sells" in js.text
    assert "renderFreshnessAnnotations" in js.text
    assert "gw2radar.api_key_permissions.v1" in js.text
    assert "gw2radar.account_connection_diagnostic.v1" in js.text
    assert "gw2radar.account_result_visibility.v1" in js.text
    assert "Result visibility" in js.text
    assert "blocked or waiting" in js.text
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
    assert 'const permissions = await fetchJson("/account/api-key/permissions")' in js.text
    assert 'const firstRun = await fetchJson("/account/first-run-summary")' in js.text
    assert "renderFirstRunSummary(firstRun)" in js.text
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
    assert "loadAchievementRouteOperatorReleaseDashboard" in js.text
    assert "exportAchievementRouteOperatorReleaseDashboard" in js.text
    assert "loadAchievementRouteReleaseExportPacket" in js.text
    assert "exportAchievementRouteReleaseExportPacket" in js.text
    assert "exportAchievementRouteReleaseExportPacketManifest" in js.text
    assert "writeAchievementRouteReleaseExportArtifacts" in js.text
    assert "loadAchievementRouteReleaseExportArtifacts" in js.text
    assert "openAchievementRouteReleaseExportArtifact" in js.text
    assert "loadAchievementRouteReleaseExportBundle" in js.text
    assert "downloadAchievementRouteReleaseExportBundle" in js.text
    assert "verifyAchievementRouteReleaseExportBundle" in js.text
    assert "recordAchievementRouteReleaseExportBundleVerificationAudit" in js.text
    assert "loadAchievementRouteReleaseExportBundleVerificationAudit" in js.text
    assert "exportAchievementRouteReleaseExportBundleVerificationAuditCsv" in js.text
    assert "loadAchievementRouteOperatorHandoffChecklist" in js.text
    assert "exportAchievementRouteOperatorHandoffChecklistCsv" in js.text
    assert "loadAchievementRouteReleaseNotes" in js.text
    assert "exportAchievementRouteReleaseNotesCsv" in js.text
    assert "loadAchievementRouteOperatorRunbook" in js.text
    assert "exportAchievementRouteOperatorRunbookCsv" in js.text
    assert "loadAchievementRouteFinalReleaseDashboard" in js.text
    assert "exportAchievementRouteFinalReleaseDashboardCsv" in js.text
    assert "loadAchievementRouteFinalMaturityAudit" in js.text
    assert "exportAchievementRouteFinalMaturityAuditCsv" in js.text
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
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-dashboard" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verify" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/artifacts/bundle/verification-audit" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/handoff-checklist" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/release-notes" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/operator-runbook" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/final-dashboard" in js.text
    assert "/api/v1/achievement-routes/source-quality/remediation-queue/release-export-packet/final-maturity-audit" in js.text


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
        "PLAYER_USE_PATH_COMPLETENESS_AUDIT.md",
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
    assert "Player Use Path Completeness Audit" in combined
    assert "gw2radar.player_use_path_completeness_audit.v1" in combined
    assert "AccountValueEvidenceBridge" in combined
    assert "promote-reviewed" in combined
