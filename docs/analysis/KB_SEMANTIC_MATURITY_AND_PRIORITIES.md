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

Remaining maturity gap:

- Domain rule depth is still shallower than the infrastructure around it.
- Returner, build, and market domains need more reviewed rules that can safely explain paid reports.

## Reordered Priorities

1. `P12 Reviewed Returner/Build/Market Rule Packs`
2. `P13 KB Batch Validation and Promotion Planner`
3. `P14 Official Source Semantic Extraction`
4. `P15 Patch Impact to Build/Market Freshness Integration`

## Implemented In This Slice

This slice adds a deterministic semantic maturity contract:

- `GET /api/v1/kb/semantic-maturity`
- `GET /api/v1/kb/semantic-maturity/export`

The report exposes:

- semantic graph nodes and edges;
- state/entity/constraint axis extraction;
- component maturity scores;
- reordered KB priorities.
