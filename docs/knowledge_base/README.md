# GW2Radar Knowledge Base

## Purpose

GW2Radar uses one intelligence stack:

```text
Knowledge Base explains.
Knowledge Graph reasons.
Player State personalizes.
Action Engine recommends.
Report Engine monetizes.
```

The Knowledge Base is the explainable layer behind paid reports, dashboards, and future subscription features. It is not a scraped content mirror and it must not store private player data.

## Knowledge Base vs Knowledge Graph

The Knowledge Base stores human-readable knowledge:

- guides;
- source summaries;
- expert rules;
- FAQ notes;
- report templates;
- strategy explanations;
- source and license notes.

The Knowledge Graph stores machine-readable reasoning facts:

- entities;
- attributes;
- relations;
- actions;
- evidence references;
- confidence and validity windows.

Together they produce personalized, explainable, evidence-backed decision intelligence. The graph can compute that an account is missing an item; the KB explains why that item matters and how the player should think about the next step.

## System Relationship

```text
Raw Sources
  -> Evidence Store
  -> Knowledge Base <-> Knowledge Graph
  -> Inference Engine
  -> Action Recommendation
  -> Paid Report / Dashboard / Subscription
```

Layer roles:

| Layer | Role |
|---|---|
| Evidence Store | Source truth, provenance, timestamps, confidence. |
| Knowledge Base | Explanations, guides, expert rules, templates. |
| Knowledge Graph | Entities, relations, requirements, actions. |
| Player State Graph | Authorized private account state. |
| Inference Engine | Gaps, readiness, fit, price and priority calculations. |
| Action Engine | Recommendation actions and explanations. |
| Report Engine | Markdown/HTML/PDF-ready artifacts and paid gates. |
| Dashboard | Keeps advice current and drives retention. |
| Analytics | Privacy-safe product and conversion insight. |

## Core Business Opportunities

GW2Radar should organize KB work around three commercial anchors.

### Returner Account Diagnosis

Core question:

```text
I have not played GW2 for a long time. What should I do first?
```

KB support:

- 7-day and 30-day returner plans;
- mount and mobility priority;
- build recovery explanations;
- common returner mistakes;
- readiness scoring explanations.

Expected intelligence:

```text
Your travel readiness is low. Prioritize basic mount and open-world mobility recovery before advanced legendary or group content goals.
```

### Legendary Goal Planning

Core question:

```text
I want to craft a legendary. What am I missing, what should I do today, and which materials must I not sell?
```

KB support:

- legendary goal guides;
- Mystic Clover source notes;
- time-gate explanations;
- acquisition method explanations;
- do-not-sell policy.

Expected intelligence:

```text
Mystic Clover is your current main bottleneck for Aurora. Reserve related materials, prioritize time-gated acquisition paths this week, and avoid selling supporting materials.
```

### Build / Gear Transition Fit

Core question:

```text
Can my account play this build now, what am I missing, and how much will it cost to switch?
```

KB support:

- build fit rules;
- gear transition rules;
- budget alternative rules;
- build source attribution policy;
- patch freshness explanations.

Expected intelligence:

```text
Power Reaper is a low-friction open-world recovery build for your current account. Your gear match is high, conversion cost is low, and it is more suitable than a high-cost raid-oriented condition build at this stage.
```

## Monetizable Intelligence Sources

| Source | Value |
|---|---|
| Official facts | High-trust facts from GW2 API, official pages, official policy, and official patch notes. |
| Private player state | Authorized account-owned materials, unlocks, wallet, gear, achievements, and goals. |
| KB explanations | Human-readable reasoning, expert rules, templates, and source notes. |
| Graph inference | Gap, fit, readiness, price, priority, and conflict calculations. |
| Expert rules | Strategic ranking and report logic. |
| Market and patch changes | Subscription-oriented recurring value. |
| Privacy-safe aggregate trends | Product, content, and conversion insight without exposing private account data. |

Forbidden monetization inputs:

- credentials and secrets;
- raw authorized account-state data;
- account identifiers;
- copied third-party full text;
- aggressive scraped content;
- gameplay automation.

## Source Levels

| Level | Source Type | Allowed Use |
|---|---|---|
| 0 | Official API / official data | Highest-confidence facts, API compatibility, evidence store, public graph, private player state. |
| 1 | GW2 Wiki / public encyclopedia | Structured summaries, source-linked guide facts, game system KB. |
| 2 | Public build / guide sites | Build metadata and summarized requirements with attribution. |
| 3 | Community discussions | Low-confidence topic trends, FAQ discovery, guide gaps, creator opportunities. |
| 4 | Expert / internal knowledge | Expert rules, action ranking, paid report logic, product differentiation. |

## Source Registry

Current source registry and coverage analysis:

- [Official Source Registry](source_registry/official_sources.md)
- [Wiki Source Registry](source_registry/wiki_sources.md)
- [License Reference Registry](source_registry/license_reference.md)
- [Build And Guide Source Registry](source_registry/build_sources.md)
- [Competitor And Ecosystem Tool Registry](source_registry/competitor_tools.md)
- [Community Source Registry](source_registry/community_sources.md)
- [Knowledge Source Coverage Analysis](source_registry/SOURCE_COVERAGE_ANALYSIS.md)

Recent patch-note structured drafts:

- [2026 Patch Notes](patch_notes/2026/)
- [2025 Patch Notes](patch_notes/2025/)
- [2024 Patch Notes](patch_notes/2024/)

Official news structured drafts:

- [Official News](news/official/)

## Collection Pipeline

KB collection is:

```text
legal source collection
-> evidence capture
-> summary extraction
-> normalization
-> graph linking
-> rule distillation
-> review
-> publishing
```

Pipeline stages:

1. Register source before use.
2. Ingest by API, manual note, Markdown file, or summary-only web review.
3. Capture evidence and source links.
4. Extract title, summary, key entities, actions, conditions, risks, dates.
5. Normalize names to graph identifiers.
6. Link articles to graph entities, relations, and actions.
7. Distill reviewed knowledge into rules.
8. Review status before use in high-priority recommendations.
9. Publish only content that respects source and privacy constraints.

## Planned Directory Structure

```text
docs/knowledge_base/
├── README.md
├── source_registry/
│   ├── official_sources.md
│   ├── wiki_sources.md
│   ├── build_sources.md
│   └── community_sources.md
├── official/
├── game_systems/
├── legendary/
├── returner/
├── build/
├── market/
├── guild/
├── creator/
└── report_templates/
```

## Planned Code Modules

```text
src/gw2radar/kb/
├── source_registry.py
├── kb_models.py
├── kb_repository.py
├── kb_ingest.py
├── kb_extractor.py
├── kb_normalizer.py
├── kb_entity_linker.py
├── kb_rule_distiller.py
├── kb_reviewer.py
├── kb_publisher.py
├── kb_search.py
└── kb_rag.py
```

## Repository Integration Strategy

GW2Radar should keep one integrated repository:

- one constitution;
- one ontology;
- one knowledge base;
- one graph system;
- one Codex roadmap;
- one commercial roadmap.

The KB must support existing product lanes instead of becoming a separate project:

| Product Lane | KB Dependency |
|---|---|
| Returner Diagnosis | Returner KB and official/game-system KB. |
| Legendary Planner Pro | Legendary KB, market KB, official facts. |
| Build Fit Advisor | Build KB and source policy. |
| Market Radar Pro | Market KB and goal cost rules. |
| Guild Readiness | Build KB, guild KB, privacy policy. |
| Creator Intelligence | Returner, build, market, guild, and creator KB. |

## Hard Constraints

- Do not scrape aggressively.
- Do not store copyrighted full-text content.
- Preserve source links and attribution.
- Store summaries and rules, not mirrored guides.
- Mark community-derived claims as low-confidence unless reviewed.
- Do not let draft KB drive high-priority actions.
- Do not store private player data in public KB.
- Do not store credentials or secrets.
- Do not implement proxy pools or IP rotation.
