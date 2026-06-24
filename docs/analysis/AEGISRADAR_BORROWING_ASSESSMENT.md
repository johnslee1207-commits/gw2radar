# AegisRadar Borrowing Assessment

- Schema: gw2radar.aegisradar_borrowing_assessment.v1
- Status: ready_for_targeted_adaptation
- Reference repo: `D:\Projects\AegisRadar`
- Reference repo state: Read-only reference. The AegisRadar worktree has local changes, so GW2Radar must not copy files or depend on that repo at runtime.

## Summary

AegisRadar is most useful as a lifecycle and ontology operating model: domain-pack driven ingestion, separated fact/graph/ontology layers, audit-backed rule promotion, credential readiness, and a front-door UX organized around connect, choose, receive. GW2Radar should borrow those structures while keeping the GW2 player domain, privacy boundaries, and current trial stop-line.

## Reference Signals

### Process Flow

| Signal | Aegis Anchor | Pattern | GW2Radar Mapping | Decision |
| --- | --- | --- | --- | --- |
| domain_pack_pipeline | `D:\Projects\AegisRadar\README.md` | Domain Pack YAML drives extraction, scoring, audit rules, graph build, and exports. | Use reviewed GW2 KB/source packs and route source manifests as the equivalent configuration surface for planners, reports, and patch impact rules. | adopt_as_pack_lifecycle |
| shared_pipeline_steps | `D:\Projects\AegisRadar\apps\api\app\jobs\run_pipeline.py` | A regular pipeline records reusable steps and can run offline demo paths. | Consolidate repeated GW2 review, promotion, export, archive, and sign-off flows behind shared lifecycle helpers instead of adding another bespoke phase chain. | adopt_as_refactor_direction |
| control_plane_boundaries | `D:\Projects\AegisRadar\docs\admin_console.md` | Admin is an intelligence OS control plane with operable and read-only classes. | Keep GW2 operator views separate from player views: support triage and release gates are operator surfaces, while account guidance remains player-facing. | adopt_as_ux_boundary |

### Ontology

| Signal | Aegis Anchor | Pattern | GW2Radar Mapping | Decision |
| --- | --- | --- | --- | --- |
| three_layer_graph | `D:\Projects\AegisRadar\docs\graph_ontology.md` | Evidence facts, intelligence graph, and ontology graph are separate layers. | GW2Radar already separates public_game, private_player_state, and personal_intelligence. The missing Aegis-style depth is explicit ontology validation and conflict surfacing for promoted rule packs. | adopt_validation_depth |
| ontology_conflict_audit | `D:\Projects\AegisRadar\core\graph\validator.py` | Invalid ontology relations and missing evidence become audit tasks. | Route invalid GW2 rule links, unsupported patch claims, and private/public layer mismatches into review queues instead of silently excluding them. | adopt_for_kb_and_patch_rules |
| rule_dry_run_toggle | `D:\Projects\AegisRadar\apps\api\app\routes\graph.py` | Ontology rules can be dry-run, compared, viewed in history, and toggled. | Extend existing reviewed KnowledgeRule enable gates with dry-run impact counts before enabling rules that affect player recommendations. | adopt_after_trial_defects |

### Final-User UX

| Signal | Aegis Anchor | Pattern | GW2Radar Mapping | Decision |
| --- | --- | --- | --- | --- |
| three_step_user_journey | `D:\Projects\AegisRadar\docs\user_journey_guide.md` | User journey is connect data sources, choose product, receive deliverable. | Translate to GW2 player language: connect API key, choose intent (legendary, build, market, returner), receive next actions and report. | adopt_for_player_cockpit_information_architecture |
| credential_readiness_cards | `D:\Projects\AegisRadar\core\credentials\readiness.py` | Report readiness explains missing providers and disabled outputs. | Use account permission readiness and sync health as visible prerequisites for account value, Build Fit, Legendary Planner, and Market Radar outputs. | adopt_for_real_api_key_feedback |
| lineage_and_deliverables | `D:\Projects\AegisRadar\apps\web\pages\deliverables` | Deliverables and lineage are separate destinations in the user journey. | Keep GW2 reports downloadable, but expose evidence lineage inline so senior players can verify why a recommendation was made. | adopt_as_report_center_polish |

## Adopt Now

### p0_trial_key_flow_visibility: Aegis-style credential readiness for real GW2 API key flow

Reason: Recent user feedback says valid keys can connect without visible outputs. Aegis solves similar confusion with readiness cards and provider requirements.

Deliverables:
- Player-facing prerequisite status for key saved, scopes, sync job, snapshots, and selected workflow.
- No-output empty states that name the missing lifecycle step.
- Support bundle evidence names aligned with the trial defect triage classifications.

Acceptance checks:
- Real-key flow never asks for or displays raw API keys.
- Every blocked account-aware panel shows a visible next action.
- Diagnostic metadata can classify empty output without private payloads.

Maturity impact: Raises UX and support maturity from trial-ready to trial-observable.

### p1_shared_lifecycle_primitives: Replace repeated review/persist/enable/export phase chains with lifecycle primitives

Reason: The current efficiency bottleneck is repeated horizontal implementation of the same operating lifecycle. Aegis uses shared pipeline and control-plane patterns.

Deliverables:
- Shared status model for draft, reviewed, persisted, enabled, exported, archived, signed_off.
- Common audit event renderer for KB, patch, route source, and release evidence objects.
- One harness that validates lifecycle transitions for at least two existing domains.

Acceptance checks:
- No behavior regression in existing KB patch and achievement route gates.
- New lifecycle helper is covered by unit tests and one smoke harness.
- Generated artifacts remain deterministic and metadata-only.

Maturity impact: Improves delivery speed and reduces duplicate phase code.

### p2_ontology_validation_queue: Aegis-style ontology conflict and missing evidence queue for GW2 rules

Reason: GW2Radar has strong schemas and layers, but Aegis has a clearer pattern for turning invalid semantic edges into reviewable work.

Deliverables:
- Rule candidate validation against entity/action/relation schemas before promotion.
- Conflict findings for unsupported relation, missing evidence, private/public mismatch, and stale patch source.
- Markdown/CSV queue export for operator review.

Acceptance checks:
- Invalid rule candidates default to disabled and cannot affect recommendations.
- Findings cite source ids and evidence refs, not raw private payloads.
- Validated rules expose dry-run impact counts before enable.

Maturity impact: Raises KB-backed recommendation maturity from reviewed-rule MVP to auditable ontology operations.

## Defer

### d1_full_domain_pack_admin: Full Aegis-style domain pack CMS/admin

Reason: GW2Radar is in player-trial closeout; a full admin CMS would expand scope.

Deliverables:
- Post-trial operator workbench only if real reviewer throughput requires it.

Acceptance checks:
- Must not replace current simple reviewed source files during trial.

Maturity impact: Useful later for content operations, not needed for immediate player validation.

### d2_pgvector_graph_rag_stack: Postgres pgvector GraphRAG parity

Reason: Aegis uses deeper data platform pieces, but GW2Radar can validate product value locally first.

Deliverables:
- Production data layer design after trial evidence confirms demand.

Acceptance checks:
- No dependency on external vector services for MVP player flows.

Maturity impact: Production scalability improvement, not a current blocker.

## Explicit Non-Goals

- Do not copy AegisRadar CO2 or market-entry business logic into GW2Radar.
- Do not add automated trading, guaranteed profit claims, or gameplay automation.
- Do not make GW2Radar depend on D:\Projects\AegisRadar at runtime.
- Do not expose private account payloads, raw API keys, or unreviewed rule content in public artifacts.

## Next Priority

Implement p0_trial_key_flow_visibility first, then refactor repeated lifecycle code only where it directly shortens current KB, route, and release gate maintenance.
