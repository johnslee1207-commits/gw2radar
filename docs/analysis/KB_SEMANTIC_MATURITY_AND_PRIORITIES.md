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
- Generic KB promotion still needs a batch planner so operators can validate, preview, and promote many articles/rules safely.
- Guild and creator policy packs remain thinner than the personal commercial lanes.

## Reordered Priorities

1. `P13 KB Batch Validation and Promotion Planner`
2. `P14 Official Source Semantic Extraction`
3. `P15 Patch Impact to Build/Market Freshness Integration`
4. `P16 Guild/Creator Policy Rule Packs`

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
