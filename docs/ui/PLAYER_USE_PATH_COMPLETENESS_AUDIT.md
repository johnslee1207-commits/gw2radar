# Player Use Path Completeness Audit

- Schema: gw2radar.player_use_path_completeness_audit.v1
- Maturity label: ready
- Readiness score: 100.0
- Passed checks: 17
- Failed checks: 0
- Privacy boundary: raw API keys and private source payloads must not appear in this audit.

## Executable Checklist

| Check | Status | Maturity | Evidence | Limitation |
| --- | --- | --- | --- | --- |
| `ui_shell` | PASS | mature_ui_shell | GET /player and /player-ui/app.js expose required workflow markers. | None for MVP depth. |
| `player_readiness_action` | PASS | mature_dashboard_readiness | needs_review at 80.0/100 with 5 checks. | None for MVP depth. |
| `player_readiness_exports` | PASS | mature_readiness_exports | GET /api/v1/player/readiness supports markdown and csv formats without raw secret fields. | None for MVP depth. |
| `player_readiness_history` | PASS | mature_readiness_history | 2 snapshots with comparison unchanged. | None for MVP depth. |
| `account_value_diagnostics` | PASS | mature_evidence_spine | GET /api/v1/player/account-value returns account_value_snapshot.diagnostics. | None for MVP depth. |
| `account_value_history` | PASS | mature_value_history | 2 snapshots with comparison unchanged. | None for MVP depth. |
| `player_history_correlation` | PASS | mature_history_correlation | unchanged with readiness delta 0.0 and price coverage delta 0.0. | None for MVP depth. |
| `player_session_packet` | PASS | mature_session_packet | 5 evidence rows and 3 support prompts. | None for MVP depth. |
| `player_session_packet_artifacts` | PASS | mature_session_packet_artifacts | 4 files with checksum c905330b34f5. | None for MVP depth. |
| `player_support_handoff` | PASS | mature_support_handoff | needs_review with 7 next actions. | None for MVP depth. |
| `player_support_handoff_artifacts` | PASS | mature_support_handoff_artifacts | 4 files with checksum a0871bca5956. | None for MVP depth. |
| `player_support_handoff_zip_verification` | PASS | mature_support_handoff_zip_verification | zip checksum 471a97ce23c6 verified with 4 files. | None for MVP depth. |
| `player_support_handoff_zip_verification_audit` | PASS | mature_support_handoff_zip_audit | 1 audit records for support handoff zip verification. | None for MVP depth. |
| `build_fit_bridge` | PASS | mature_semantic_bridge | gw2radar.account_value_evidence_bridge.v1 with 3 source summaries and 2 remediation items. | None for MVP depth. |
| `legendary_bridge` | PASS | mature_semantic_bridge | gw2radar.account_value_evidence_bridge.v1 with 3 source summaries and 2 remediation items. | None for MVP depth. |
| `market_bridge` | PASS | mature_semantic_bridge | gw2radar.account_value_evidence_bridge.v1 with 3 source summaries and 2 remediation items. | None for MVP depth. |
| `report_export_bridge` | PASS | mature_export_metadata | POST /api/v1/builds/report writes report_manifest.json account_value_snapshot.evidence_bridge. | None for MVP depth. |

## Semantic Graph Summary

- `ApiKeyConnection` gates account-aware recommendations through permission checks and sync status.
- `PrivatePlayerState` stores private account summaries separately from public game and KB layers.
- `AccountValueSnapshot` normalizes holdings, price coverage, source diagnostics, and remediation actions.
- `AccountValueHistory` stores privacy-safe value coverage snapshots and compares value/coverage/freshness deltas.
- `AccountValueEvidenceBridge` carries the same summary-only evidence into Build Fit, Legendary Planner, Market Radar, and report artifacts.
- `PlayerReadinessSummary` aggregates sync, account value, Legendary, Market, and Build Fit bridge checks into one dashboard action.
- `PlayerReadinessExport` renders the readiness summary as Markdown and CSV for player/support comparison across sessions.
- `PlayerReadinessHistory` stores privacy-safe readiness snapshots and compares the latest two score/check states.
- `PlayerHistoryCorrelation` explains readiness deltas alongside account value, price coverage, and warning deltas.
- `PlayerSessionPacket` packages readiness, value, correlation, and debug-safe support prompts without raw private payloads.
- `PlayerSessionPacketArtifacts` writes local JSON/Markdown/CSV/manifest files with checksums and path-safe retrieval.
- `PlayerSupportHandoffBundle` combines packet artifact metadata with account debug review status for privacy-safe support triage.
- `PlayerSupportHandoffArtifacts` archives handoff JSON/Markdown/CSV/manifest files with checksums and path-safe retrieval.
- `PlayerSupportHandoffZipVerification` transfers handoff artifacts as a read-only zip and verifies schema, checksum, whitelist, and no-secret boundaries from bytes.
- `PlayerSupportHandoffZipVerificationAudit` records verification outcomes as metadata-only support evidence without storing zip bytes.
- `ReportArtifactManifest` records bridge metadata without storing raw API keys or unredacted private payloads.

## Known Limits

- Official price refresh depends on the external GW2 API gateway; this audit verifies the UI/API contract and existing dedicated refresh tests cover gateway behavior.
- The audit uses demo graph and deterministic local database data; real player accounts can still encounter GW2 API rate limits or missing optional permissions.
- UI validation here is static plus API-level; full browser visual polish should remain covered by browser screenshot checks when layout changes are substantial.

## Next Priority

Add a support handoff readiness checklist that summarizes artifact, zip verification, and audit gates for support operators.
