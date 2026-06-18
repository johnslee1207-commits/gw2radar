# GW2Radar Benchmark Matrix

## Strategic Position

GW2Radar should be a Personal GW2 Account Advisor. It should not become another account asset explorer, build database, combat simulator, or generic chatbot.

## Reference Links

- https://gw2efficiency.com/
- https://www.wowhead.com/planner
- https://pathofbuilding.community/
- https://snowcrows.com/builds
- https://metabattle.com/wiki/MetaBattle_Wiki
- https://en.wikipedia.org/wiki/Retrieval-augmented_generation

## Comparison Matrix

| Benchmark | Core Capability | Copy | Avoid | GW2Radar Differentiation |
| --- | --- | --- | --- | --- |
| gw2efficiency | Official API account data, assets, crafting, shopping list | Account sync, inventory index, owned-material reuse | Asset-only product, raw private payload exposure | Goal-oriented next actions and do-not-sell protection |
| Wowhead Planner | Player-friendly profile planning | Readiness, plain-language recommendations, onboarding | Database-only flow, hidden assumptions | Returner Account Advisor with evidence-backed recovery plan |
| Path of Building | Structured build computation | Build objects, breakdown, version awareness | Full simulator promises, absolute meta claims | Account-to-build fit and transition cost |
| Snow Crows | Expert GW2 builds and guides | Metadata, attribution, role and mode structure | Copying guide text, unreviewed strong claims | Reviewed build source references plus fit check |
| MetaBattle | Broad build database and mode coverage | Mode taxonomy, quality hints, source freshness | Over-trusting community labels | Coverage plus account-specific readiness and review gates |
| KG/RAG | Evidence-backed explanations | Raw evidence, KB, rules, freshness, report provenance | LLM-invented facts, private/public leakage | Graph/rule decisions explained by reviewed evidence |

## Confirmed Evolution Route

1. Benchmark Research Pack.
2. Player UI end-to-end smoke.
3. AccountInventoryIndex.
4. GoalOwnedMaterialResolver and ShoppingList.
5. Legendary Planner Pro deepening.
6. Returner Account Advisor independent diagnose.
7. BuildSourceRegistry.
8. BuildFitBreakdown 2.0.
9. Patch-triggered build review.
10. RAGExplanationService.
11. Commercial Operations Dashboard.

## Current Implementation Alignment

- Account sync, refresh queue, SecretStore, and private layer writing exist at MVP depth.
- Legendary, Build Fit, Market, Returner, Guild, Creator, report artifacts, entitlement, and Player UI exist at MVP depth.
- KB source registry, raw evidence, KnowledgeArticle, KnowledgeRule, rule distillation, review gates, patch audit, and release readiness exist at MVP depth.
- Next engineering emphasis should shift from feature presence to production depth, data completeness, and end-to-end player verification.

## Development Guardrails

- Do not copy third-party guide bodies.
- Store links, metadata, short summaries, evidence refs, and attribution.
- Keep API keys and private account payloads out of logs, public KB, reports, and queue payloads.
- Do not claim guaranteed profit or absolute meta correctness.
- RAG may explain reviewed evidence-backed results; it must not invent missing facts.
