# Player Use Path Completeness Audit

- Schema: gw2radar.player_use_path_completeness_audit.v1
- Maturity label: ready
- Readiness score: 100.0
- Passed checks: 42
- Failed checks: 0
- Privacy boundary: raw API keys and private source payloads must not appear in this audit.

## Executable Checklist

| Check | Status | Maturity | Evidence | Limitation |
| --- | --- | --- | --- | --- |
| `ui_shell` | PASS | mature_ui_shell | GET /player and /player-ui/app.js expose required workflow markers. | None for MVP depth. |
| `account_first_run_summary` | PASS | mature_first_run_empty_result_guidance | missing_key with 5 state cards. | None for MVP depth. |
| `account_sync_worker_health` | PASS | mature_account_sync_worker_health | idle with queue depth 0. | None for MVP depth. |
| `account_sync_gateway_contract` | PASS | mature_gateway_error_contract | account_sync_not_ready | None for MVP depth. |
| `public_refresh_worker_health` | PASS | mature_public_refresh_worker_health | idle with queue depth 0. | None for MVP depth. |
| `market_price_refresh_diagnostics` | PASS | mature_market_price_refresh_diagnostics | idle with 0 gateway diagnostics. | None for MVP depth. |
| `gateway_incident_timeline` | PASS | mature_gateway_incident_timeline | clear with 1 events. | None for MVP depth. |
| `gateway_incident_history` | PASS | mature_gateway_incident_history | 2 snapshots with comparison unchanged. | None for MVP depth. |
| `gateway_incident_review_notes` | PASS | mature_gateway_incident_review_notes | 1 notes with assigned and closed lifecycle evidence. | None for MVP depth. |
| `support_case_incident_dashboard` | PASS | mature_support_case_incident_dashboard | 4 cards with status ready. | None for MVP depth. |
| `support_case_incident_packet` | PASS | mature_support_case_incident_packet | 4 files with checksum 1a0a93e0983e. | None for MVP depth. |
| `support_case_incident_packet_zip_verification` | PASS | mature_support_case_incident_packet_zip_verification | zip checksum 7d6cb402d6e4 verified with 4 files. | None for MVP depth. |
| `support_case_incident_packet_zip_verification_audit` | PASS | mature_support_case_incident_packet_zip_verification_audit | 10 metadata-only zip verification audit records available. | None for MVP depth. |
| `support_case_incident_handoff_checklist` | PASS | mature_support_case_incident_handoff_checklist | 5 gates summarized with 0 missing gates. | None for MVP depth. |
| `support_case_incident_operator_packet_artifacts` | PASS | mature_support_case_incident_operator_packet_artifacts | 9 metadata files written for operator handoff. | None for MVP depth. |
| `support_case_incident_operator_packet_zip_verification` | PASS | mature_support_case_incident_operator_packet_zip_verification | operator zip checksum 7f7ebc5e9e22 verified with 9 files. | None for MVP depth. |
| `support_case_incident_operator_packet_zip_verification_audit` | PASS | mature_support_case_incident_operator_packet_zip_verification_audit | 6 metadata-only operator zip audit records available. | None for MVP depth. |
| `support_case_incident_final_handoff_checklist` | PASS | mature_support_case_incident_final_handoff_checklist | 9 operator files and 1 audit records gated. | None for MVP depth. |
| `support_case_incident_final_handoff_packet_artifacts` | PASS | mature_support_case_incident_final_handoff_packet_artifacts | 6 final handoff files with checksum 5c686578bf1f. | None for MVP depth. |
| `support_case_incident_final_handoff_packet_zip_verification_audit` | PASS | mature_support_case_incident_final_handoff_packet_zip_verification_audit | final handoff zip checksum 7dae241af9ee verified with 6 files. | None for MVP depth. |
| `support_case_incident_closure_dashboard` | PASS | mature_support_case_incident_closure_dashboard | go at 100.0 with 1 final audits. | None for MVP depth. |
| `support_case_incident_closure_packet_artifacts` | PASS | mature_support_case_incident_closure_packet_artifacts | 7 closure files with checksum 482d8e7533ec. | None for MVP depth. |
| `player_readiness_action` | PASS | mature_dashboard_readiness | needs_review at 80.0/100 with 5 checks. | None for MVP depth. |
| `player_readiness_exports` | PASS | mature_readiness_exports | GET /api/v1/player/readiness supports markdown and csv formats without raw secret fields. | None for MVP depth. |
| `player_readiness_history` | PASS | mature_readiness_history | 2 snapshots with comparison unchanged. | None for MVP depth. |
| `account_value_diagnostics` | PASS | mature_evidence_spine | GET /api/v1/player/account-value returns account_value_snapshot.diagnostics. | None for MVP depth. |
| `account_value_history` | PASS | mature_value_history | 2 snapshots with comparison unchanged. | None for MVP depth. |
| `player_history_correlation` | PASS | mature_history_correlation | unchanged with readiness delta 0.0 and price coverage delta 0.0. | None for MVP depth. |
| `player_session_packet` | PASS | mature_session_packet | 7 evidence rows and 3 support prompts. | None for MVP depth. |
| `player_session_packet_artifacts` | PASS | mature_session_packet_artifacts | 4 files with checksum 172064af59b9. | None for MVP depth. |
| `player_support_handoff` | PASS | mature_support_handoff | needs_review with 7 next actions. | None for MVP depth. |
| `player_support_handoff_artifacts` | PASS | mature_support_handoff_artifacts | 4 files with checksum f2cf797d2790. | None for MVP depth. |
| `player_support_handoff_zip_verification` | PASS | mature_support_handoff_zip_verification | zip checksum 0c543439e3e1 verified with 4 files. | None for MVP depth. |
| `player_support_handoff_zip_verification_audit` | PASS | mature_support_handoff_zip_audit | 1 audit records for support handoff zip verification. | None for MVP depth. |
| `player_support_handoff_readiness` | PASS | mature_support_handoff_readiness | ready with 1 audit records. | None for MVP depth. |
| `player_support_handoff_operator_packet` | PASS | mature_support_handoff_operator_packet | 5 runbook steps and 3 transfer files. | None for MVP depth. |
| `player_support_handoff_dashboard` | PASS | mature_support_handoff_dashboard | 5 dashboard cards and 1 audit records. | None for MVP depth. |
| `player_support_handoff_final_archive` | PASS | mature_support_handoff_final_archive | 6 files with zip checksum fa3d2509a455. | None for MVP depth. |
| `build_fit_bridge` | PASS | mature_semantic_bridge | gw2radar.account_value_evidence_bridge.v1 with 3 source summaries and 2 remediation items. | None for MVP depth. |
| `legendary_bridge` | PASS | mature_semantic_bridge | gw2radar.account_value_evidence_bridge.v1 with 3 source summaries and 2 remediation items. | None for MVP depth. |
| `market_bridge` | PASS | mature_semantic_bridge | gw2radar.account_value_evidence_bridge.v1 with 3 source summaries and 2 remediation items. | None for MVP depth. |
| `report_export_bridge` | PASS | mature_export_metadata | POST /api/v1/builds/report writes report_manifest.json account_value_snapshot.evidence_bridge. | None for MVP depth. |

## Semantic Graph Summary

- `ApiKeyConnection` gates account-aware recommendations through permission checks and sync status.
- `AccountFirstRunSummary` explains empty account-aware result states across missing key, limited permissions, sync queue, and private-layer write gates.
- `AccountSyncWorkerHealth` exposes bounded worker-loop health, queue depth, retry depth, failed depth, latest jobs, and safe next actions.
- `AccountSyncGatewayContract` returns structured user-facing error envelopes for missing key, permission, rate-limit, and API client failure states.
- `PublicRefreshWorkerHealth` exposes public static refresh queue depth, retry depth, failed depth, latest jobs, and safe next actions.
- `MarketPriceRefreshDiagnostics` explains official commerce price refresh status, retryability, player action, and no-trading boundary.
- `GatewayIncidentTimeline` correlates account sync, public refresh, and market price refresh metadata into one player-facing incident view.
- `GatewayIncidentHistory` persists metadata-only incident snapshots, compares retry/failure deltas, and exports Markdown/CSV support evidence.
- `GatewayIncidentReviewNote` lets support annotate, assign, close, and export metadata-only incident follow-up state.
- `SupportCaseIncidentDashboard` aggregates gateway incidents, support review audits, and handoff readiness into one operator case view.
- `SupportCaseIncidentPacket` writes dashboard JSON/Markdown/CSV/manifest files with checksums and path-safe retrieval.
- `SupportCaseIncidentPacketZipVerification` downloads and verifies read-only packet zip bundles for checksum, schema, whitelist, and no-secret boundaries.
- `PrivatePlayerState` stores private account summaries separately from public game and KB layers.
- `AccountValueSnapshot` normalizes holdings, price coverage, source diagnostics, and remediation actions.
- `AccountValueHistory` stores privacy-safe value coverage snapshots and compares value/coverage/freshness deltas.
- `AccountValueEvidenceBridge` carries the same summary-only evidence into Build Fit, Legendary Planner, Market Radar, and report artifacts.
- `PlayerReadinessSummary` aggregates sync, account value, Legendary, Market, and Build Fit bridge checks into one dashboard action.
- `PlayerReadinessExport` renders the readiness summary as Markdown and CSV for player/support comparison across sessions.
- `PlayerReadinessHistory` stores privacy-safe readiness snapshots and compares the latest two score/check states.
- `PlayerHistoryCorrelation` explains readiness deltas alongside account value, price coverage, and warning deltas.
- `PlayerSessionPacket` packages readiness, value, correlation, gateway incident history, and debug-safe support prompts without raw private payloads.
- `PlayerSessionPacketArtifacts` writes local JSON/Markdown/CSV/manifest files with checksums and path-safe retrieval.
- `PlayerSupportHandoffBundle` combines packet artifact metadata with account debug review status for privacy-safe support triage.
- `PlayerSupportHandoffArtifacts` archives handoff JSON/Markdown/CSV/manifest files with checksums and path-safe retrieval.
- `PlayerSupportHandoffZipVerification` transfers handoff artifacts as a read-only zip and verifies schema, checksum, whitelist, and no-secret boundaries from bytes.
- `PlayerSupportHandoffZipVerificationAudit` records verification outcomes as metadata-only support evidence without storing zip bytes.
- `PlayerSupportHandoffReadinessChecklist` summarizes artifact, zip, verification, and audit gates for support operators.
- `PlayerSupportHandoffOperatorPacket` packages the readiness checklist, audit summary, zip manifest, runbook, and transfer files for support workflows.
- `PlayerSupportHandoffDashboard` aggregates artifacts, zip verification, audit, readiness, and operator packet state into one support case view.
- `PlayerSupportHandoffFinalArchiveManifest` packages dashboard, operator packet, readiness checklist, and audit exports into deterministic local files and a verified zip.
- `SupportCaseIncidentPacketZipVerificationAudit` records incident packet zip verification outcomes as metadata-only support evidence.
- `SupportCaseIncidentHandoffChecklist` summarizes dashboard, packet, zip, verification, and audit gates into one operator-ready handoff view.
- `SupportCaseIncidentOperatorPacketArtifacts` write deterministic metadata files for incident support handoff.
- `SupportCaseIncidentOperatorPacketZipVerification` packages operator packet artifacts as a read-only zip and verifies checksum, schema, whitelist, and no-secret boundaries.
- `SupportCaseIncidentOperatorPacketZipVerificationAudit` records operator packet zip verification outcomes as metadata-only support evidence.
- `SupportCaseIncidentFinalHandoffChecklist` combines operator artifact, zip, verification, and audit gates into a support closure view.
- `SupportCaseIncidentFinalHandoffPacketArtifacts` write final closure checklist, manifest, operator artifact manifest, and audit export files with checksums.
- `SupportCaseIncidentFinalHandoffPacketZipVerificationAudit` verifies final handoff packet zip archives and records metadata-only closure audit evidence.
- `SupportCaseIncidentClosureDashboard` aggregates incident packet, operator packet, final packet, zip audit, and final go/no-go state.
- `SupportCaseIncidentClosurePacketArtifacts` write closure dashboard, final audit, checksum manifest, and path-safe retrieval metadata files.
- `ReportArtifactManifest` records bridge metadata without storing raw API keys or unredacted private payloads.

## Known Limits

- Official price refresh depends on the external GW2 API gateway; this audit verifies the UI/API contract and dedicated refresh tests cover delayed gateway behavior.
- The audit uses demo graph and deterministic local database data; real player accounts can still encounter GW2 API rate limits or missing optional permissions.
- UI validation here is static plus API-level; full browser visual polish should remain covered by browser screenshot checks when layout changes are substantial.

## Next Priority

Build Support Case Incident Closure Packet zip archive with whitelist verification and metadata-only audit.
