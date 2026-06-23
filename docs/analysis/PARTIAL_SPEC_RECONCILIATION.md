# Partial Spec Reconciliation

- Schema: gw2radar.partial_spec_reconciliation.v1
- Partial specs: 14
- Reconciled specs: 14
- Needs review: 0

## Gap Type Counts

- broad_roadmap: 2
- governance_aligned: 1
- implemented_core_team_model: 1
- implemented_for_mock_payment: 1
- implemented_with_content_depth_backlog: 1
- implemented_with_live_gateway_limit: 2
- legacy_spec_drift: 2
- post_mvp_master_plan: 1
- superseded_by_delivery_lifecycle: 1
- trial_defect_operationalized: 1
- ui_guide_partially_operationalized: 1

## Reconciliation Table

| Spec | Gap Type | Status | Evidence Tests | Recommended Action |
| --- | --- | --- | --- | --- |
| [GW2Radar Commercial Opportunity Full Implementation Roadmap — Codex Spec](docs/analysis/GW2Radar_Commercial_Opportunity_Full_Implementation_Roadmap_Codex_Spec.md) | broad_roadmap | reconciled | tests/test_report_productization.py, tests/test_market_api.py, tests/test_build_fit_api.py | Keep implemented commercial slices covered by report, entitlement, guild, creator, market, build, and player UI tests; schedule only explicitly selected roadmap gaps. |
| [GW2Radar Knowledge Base, Knowledge Graph & Commercial Intelligence Implementation Plan](docs/analysis/GW2Radar_KB_Graph_Commercial_Intelligence_Implementation_Plan.md) | broad_roadmap | reconciled | tests/test_kb_backed_report.py, tests/test_kb_release_readiness.py, tests/test_patch_admin_workflow_api.py | Prioritize reviewed rule pack content and source-evidence quality, not new lifecycle plumbing. |
| [GW2Radar / GW2 Progression 全部规划与系统设计汇总（统一主文档）](docs/analysis/GW2Radar_Master_Planning_Summary.md) | post_mvp_master_plan | reconciled | tests/test_post_mvp_roadmap.py, tests/test_closure_readiness.py, tests/test_no_auto_trading.py | Use the post-MVP production roadmap gate to schedule Phase A first and keep SaaS, autonomous agents, and real billing as later explicit stages. |
| [GW2Radar MVP 0.1 研制规范](docs/analysis/GW2Radar_MVP_0_1_Codex_Development_Spec.md) | legacy_spec_drift | reconciled | tests/test_goal_gap.py, tests/test_graph_layers.py, tests/test_account_connection_diagnostic.py | Use current PRD/SDD, MVP docs, and stage gate as source of truth; keep this spec as historical input. |
| [GW2Radar Official GW2 API Compatibility Layer — Codex Development Spec](docs/analysis/GW2Radar_Official_GW2_API_Compatibility_Layer_Codex_Spec.md) | implemented_with_live_gateway_limit | reconciled | tests/test_gw2_api_client_official_contract.py, tests/test_gw2_api_key_safety.py, tests/test_gw2_api_rate_limit_behavior.py | Do not expand scope into live certification. Keep fake gateway and contract tests strict, then add optional live smoke only behind explicit operator configuration. |
| [GW2Radar Project Constitution & API Access Governance — Codex Development Spec](docs/analysis/GW2Radar_Project_Constitution_API_Governance_Codex_Spec.md) | governance_aligned | reconciled | tests/test_constitution_compliance_security.py, tests/test_no_auto_trading.py, tests/test_workspace_hygiene.py | Keep governance enforced through stage gate, no-secret tests, and workspace hygiene; avoid adding SaaS or automation scope. |
| [GW2Radar Senior Player User Guide](docs/analysis/SENIOR_PLAYER_USER_GUIDE.md) | ui_guide_partially_operationalized | reconciled | tests/test_player_ui.py, tests/test_player_ui_e2e_smoke.py, tests/test_player_dashboard_completion.py | Use future UI slices for browser screenshots and senior-player copy refinement when layout changes are made. |
| [Real User Trial Readiness](docs/analysis/TRIAL_DEFECT_TRIAGE_READINESS.md) | trial_defect_operationalized | reconciled | tests/test_trial_defect_triage.py, tests/test_final_closeout_dashboard.py, tests/test_account_connection_diagnostic.py | Use this track for real trial defect triage only; do not reopen broad phase expansion unless a concrete user defect requires it. |
| [MVP 0.1.2 Report Export Package](docs/mvp/MVP_0_1_2_REPORT_EXPORT_PACKAGE.md) | superseded_by_delivery_lifecycle | reconciled | tests/test_report_productization.py, tests/test_delivery_lifecycle.py, tests/test_export_package.py | Treat this as superseded by delivery lifecycle regression unless a legacy export route is explicitly requested. |
| [MVP 0.1.5 Evidence Freshness and Confidence Rules](docs/mvp/MVP_0_1_5_EVIDENCE_QUALITY_RULES.md) | implemented_with_content_depth_backlog | reconciled | tests/test_evidence_quality.py, tests/test_source_attribution.py, tests/test_kb_report_quality.py | Invest next in reviewed content depth and source freshness, not new evidence framework mechanics. |
| [GW2Radar MVP 0.1 Codex Development Spec](docs/mvp/MVP_0_1_CODEX_DEVELOPMENT_SPEC.md) | legacy_spec_drift | reconciled | tests/test_markdown_report.py, tests/test_graph_builder.py, tests/test_report_no_secret_leakage.py | Keep for audit traceability; rely on current registry and maturity audits for execution priority. |
| [MVP 0.2.0 Official API Compatibility Hardening](docs/mvp/MVP_0_2_0_OFFICIAL_API_COMPATIBILITY_HARDENING.md) | implemented_with_live_gateway_limit | reconciled | tests/test_gw2_api_client_official_contract.py, tests/test_gw2_api_permissions.py, tests/test_gw2_api_batching.py | Add optional live smoke documentation only after local contract stability remains clean. |
| [MVP 0.3.0 Paid Report Engine](docs/mvp/MVP_0_3_0_PAID_REPORT_ENGINE.md) | implemented_for_mock_payment | reconciled | tests/test_report_entitlement.py, tests/test_payment_provider_mock.py, tests/test_paid_report_api_routes.py | Keep mock payment and entitlement integration; defer real provider work until explicitly requested. |
| [MVP 0.3.5 Guild / Static Readiness Console](docs/mvp/MVP_0_3_5_GUILD_READINESS_CONSOLE.md) | implemented_core_team_model | reconciled | tests/test_guild_api.py, tests/test_team_consent.py, tests/test_member_privacy_summary.py | Preserve privacy-safe team modeling and avoid expanding into full collaboration or subscription administration. |

## Next Priority

Promote reconciled partial specs into a smaller backlog: reviewed content depth, optional live API smoke documentation, and UI visual polish only when explicitly scheduled.
