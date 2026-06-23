# Post-MVP Production Roadmap

- Schema: gw2radar.post_mvp_production_roadmap.v1
- Current MVP status: ready_to_close_mvp_stage
- Blocking current MVP: false
- Phase count: 6
- Next phase: phase_a_trust_credential_mvp

## Decision

Start Phase A only; keep production SaaS, real billing, team workspace, and autonomous agents as later explicit stages.

## Source Documents

- [docs/analysis/GW2Radar_Trust_Credential_Architecture.md](docs/analysis/GW2Radar_Trust_Credential_Architecture.md)
- [docs/analysis/GW2Radar_Production_SaaS_Architecture.md](docs/analysis/GW2Radar_Production_SaaS_Architecture.md)
- [docs/analysis/GW2Radar_Master_Planning_Summary.md](docs/analysis/GW2Radar_Master_Planning_Summary.md)

## Phases

| Priority | Phase | Status | Scope | Deferred |
| --- | --- | --- | --- | --- |
| 1 | Phase A Trust & Credential MVP | next_recommended | session-only BYOK mode, credential mode model, permission explanation UI/API, credential usage audit summary, revoke/delete/rotate UX | team workspace credential sharing, KMS production vault |
| 2 | Phase B Report Product Close Loop | recommended_after_phase_a | clear report product contracts, preview vs full report boundary, mock license and entitlement lifecycle, delivery artifacts through shared lifecycle | real payment provider, email delivery provider |
| 3 | Phase C Progression Decision Engine v1 | recommended_after_phase_b | manual action model, scoring model, Top-K recommendation API, KB-backed recommendation explanation | automatic trading, automatic gameplay execution, profit guarantees |
| 4 | Phase D 7-Day Planning / DAG | post_phase_c | goal interpreter, action dependency graph, 7-day plan generator, plan export Markdown/CSV/JSON | real-time autonomous replanning |
| 5 | Phase E Production SaaS Foundation | large_separate_stage | auth/session model, workspace model, PostgreSQL migration plan, Redis/cache/queue plan, object storage abstraction, billing guard abstraction | full multi-tenant SaaS launch, real payment integration |
| 6 | Phase F Growth / Retention | after_saas_foundation | weekly report job, report history, safe share preview, mock email delivery abstraction, subscription retention UX | public sharing of private account payloads, real email provider lock-in |

## Phase A Acceptance

- raw keys never appear in logs, URLs, reports, or front-end storage
- session-only mode requires no persisted secret
- encrypted persistent mode remains local-first unless production mode is explicit
