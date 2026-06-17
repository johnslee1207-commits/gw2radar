# KB Semantic Maturity And Priorities

## Snapshot

GitNexus status at analysis time:

- Indexed commit: `d20fb20`
- Current commit: `d20fb20`
- Status: up-to-date

GitNexus query axes used:

- `KnowledgeRule PatchReviewDashboard PatchRuleAudit KnowledgeArticle SourceRegistry`
- `enum OR class State OR class Status OR class Phase`
- `raise OR ValueError OR HIGH_PRIORITY_THRESHOLD OR enabled`

## Maturity Summary

The KB implementation now has a mature MVP semantic spine:

- Source registry and KB schema are implemented.
- Markdown loading, entity linking, and reviewed rule distillation exist.
- KB explanations are restricted to reviewed enabled rules.
- Paid report artifacts include KB quality and patch audit provenance.
- Official PDF inventory/evidence and patch/news summary stubs exist.
- Patch review has review, persist, enable, audit, dashboard, export, and admin workflow APIs.

Remaining maturity gap after P12:

- Returner, build, and market now have reviewed disabled rule packs.
- Generic KB promotion now has a batch planner for validation, distillation preview, rule pack preview, and deterministic exports.
- Official source summaries now expose summary-only semantic hints, ontology links, action hints, and evidence refs.
- Patch review and source semantic hints now surface manual build/market freshness notices in APIs and reports.
- Guild and creator policy packs now exist as reviewed disabled rules with confirmation-gated import.

## Reordered Priorities

1. `P18 Admin Release Console Workflow`

## Implemented In This Slice

This slice adds a deterministic semantic maturity contract:

- `GET /api/v1/kb/semantic-maturity`
- `GET /api/v1/kb/semantic-maturity/export`

The report exposes:

- semantic graph nodes and edges;
- state/entity/constraint axis extraction;
- component maturity scores;
- reordered KB priorities.

## P12 Implemented

P12 turns KB infrastructure into reviewed commercial rule content:

- `GET /api/v1/kb/rule-packs`
- `GET /api/v1/kb/rule-packs/{pack_id}`
- `POST /api/v1/kb/rule-packs/{pack_id}/import`

Included packs:

- `returner_recovery`
- `build_fit_freshness`
- `market_retention`

Safety contract:

- all pack rules are `reviewed`;
- all pack rules are imported with `enabled=false`;
- import requires explicit confirmation;
- duplicate imports are skipped deterministically;
- market rules are checked against forbidden market language.

## P13 Implemented

P13 adds a generic KB promotion planner:

- `GET /api/v1/kb/promotion-plan`
- `GET /api/v1/kb/promotion-plan/export`

Planner coverage:

- batch validates article linked entities and linked actions;
- previews reviewed rule articles that can become `KnowledgeRule` records;
- keeps previewed distilled rules `enabled=false`;
- previews reviewed domain rule packs for import readiness;
- summarizes blockers across articles and packs;
- exports deterministic Markdown and CSV.

The planner is intentionally read-only. Persistence still happens through existing reviewed/confirmed distillation and rule-pack import APIs.

## P14 Implemented

P14 adds summary-only official source semantic extraction:

- `GET /api/v1/kb/source-semantics`
- `GET /api/v1/kb/source-semantics/export`

Extractor coverage:

- scans official, official news, and patch-note Markdown summaries;
- extracts evidence refs from source stubs;
- derives ontology links from linked entities and structured source fields;
- derives action hints for build freshness, market watchlist review, product context review, and API operations;
- reports blockers for missing evidence or missing ontology links;
- exports deterministic Markdown and CSV.

The extractor reads Markdown summaries only. It does not read raw PDFs, does not copy source text, and does not promote draft facts to reviewed rules.

## P15 Implemented

P15 connects patch impact and source semantic hints to commercial freshness review:

- `GET /api/v1/builds/{build_id}/patch-freshness`
- `GET /api/v1/market/patch-freshness`

Integration coverage:

- reviewed patch dashboard items can create build freshness notices;
- reviewed patch dashboard items can create market watchlist freshness notices;
- source semantic hints can create manual review notices even before rule promotion;
- build fit responses include patch freshness notices;
- market watchlist responses include patch freshness notices;
- build and market paid report Markdown can include a patch freshness review section.

Safety boundary:

- notices are manual-review-only;
- no automatic gear/build changes are performed;
- no automated orders or trading actions are performed;
- evidence refs remain attached to notices.

## P16 Implemented

P16 extends reviewed domain rule packs beyond personal commercial lanes:

- `guild_privacy_readiness`
- `creator_signal_safety`

Guild policy coverage:

- consent-based readiness summaries;
- role coverage and readiness bands only;
- revoked consent exclusion from readiness calculations;
- no account-level detail exposure in rule explanations.

Creator policy coverage:

- community-derived opportunities remain discovery signals until reviewed;
- attribution and conservative confidence are preserved;
- concise summaries and source links are preferred;
- copied community content is rejected by existing no-mass-copy policy checks.

Safety contract remains unchanged:

- all policy pack rules are `reviewed`;
- all policy pack rules are imported with `enabled=false`;
- import requires explicit confirmation;
- duplicate imports are skipped deterministically.

## P17 Implemented

P17 adds a KB release readiness and operating playbook gate:

- `GET /api/v1/kb/release-readiness`
- `GET /api/v1/kb/release-readiness/export`

Checklist coverage:

- semantic maturity baseline;
- reviewed disabled rule packs;
- promotion plan blockers;
- source semantics and evidence coverage;
- patch dashboard and audit trail readiness;
- operating boundaries for import and enable gates.

Operator playbook coverage:

- selected rule packs must be imported with explicit confirmation;
- only reviewed KnowledgeRule records should be enabled;
- source semantics, promotion plan, patch dashboard, and audit exports should be archived for release evidence;
- release readiness is read-only and does not change KB state.

Next maturity gap:

- provide a front-end friendly admin workflow bundle for checklist display, exports, import, enable, and audit actions while preserving all confirmation gates.
