# GW2Radar Knowledge Base, Knowledge Graph & Commercial Intelligence Implementation Plan

```text
Document ID: GW2RADAR_KB_GRAPH_COMMERCIAL_INTELLIGENCE_IMPLEMENTATION_PLAN
Project: GW2Radar
Version: v0.4
Status: Codex-ready System Implementation Plan
Primary Audience:
  - Codex
  - Product Owner
  - Architecture Reviewer
  - Backend Developer
  - Knowledge Engineer
  - Commercial Operator
```

---

## 0. Purpose

This document merges three major design discussions into one implementation-ready system plan:

```text
1. Why GW2Radar needs a Knowledge Base and how to collect/organize it.
2. How Knowledge Base, Knowledge Graph, Evidence Store, Player State Graph, Inference Engine, and Report Engine relate.
3. How the three core commercial opportunities map to all implementation modules.
```

The goal is to make GW2Radar implementable as a real product, not just a set of reports or disconnected tools.

The final system principle is:

```text
Knowledge Base explains.
Knowledge Graph reasons.
Player State personalizes.
Action Engine recommends.
Report Engine monetizes.
```

---

## 1. Core Commercial Opportunities

GW2Radar should focus on three primary commercial opportunities.

These are not isolated product ideas. They are the commercial anchors that organize all system modules.

```text
Opportunity 1: Returner Account Diagnosis
Opportunity 2: Legendary Goal Planning
Opportunity 3: Build / Gear Transition Fit
```

Everything else — knowledge base, graph, API, market, patch, guild, creator tools, report engine, website, payment, analytics — should support or extend these three.

---

## 2. Opportunity 1 — Returner Account Diagnosis

### 2.1 Core User Question

```text
I have not played GW2 for a long time. What should I do first?
```

### 2.2 Business Nature

This opportunity solves:

```text
Cognitive recovery cost.
```

Returning players often do not know:

```text
1. What changed in the game.
2. Which systems they have unlocked.
3. Which systems they should prioritize.
4. Whether their characters are still playable.
5. Whether their gear/builds are outdated.
6. Which goals should be postponed.
7. What a practical 7-day or 30-day recovery route looks like.
```

### 2.3 Product Form

```text
Free Returner Preview
→ Paid Returner Diagnosis Report
→ 7-day / 30-day Returner Recovery Plan
→ Subscription upgrade
```

### 2.4 Required Capabilities

```text
1. Account Snapshot Sync.
2. Private Player State Graph.
3. Returner Knowledge Base.
4. AccountReadiness scoring.
5. Missing unlock inference.
6. ReturnerPath generation.
7. Report Engine.
8. Paid Report gating.
9. Website landing page.
```

### 2.5 Required Knowledge Base Domains

```text
docs/knowledge_base/returner/
├── returner_7_day_plan.md
├── returner_30_day_plan.md
├── mount_priority.md
├── build_recovery.md
└── common_returner_mistakes.md
```

### 2.6 Core Intelligence Output

Without KB:

```text
You are missing some unlocks.
```

With KB + Graph:

```text
Your travel readiness is low. Prioritize basic mount and open-world mobility recovery before advanced legendary or group content goals.
```

This explanation is the monetizable intelligence.

---

## 3. Opportunity 2 — Legendary Goal Planning

### 3.1 Core User Question

```text
I want to craft a legendary. What am I missing, what should I do today, and which materials must I not sell?
```

### 3.2 Business Nature

This opportunity solves:

```text
Long-term goal planning cost.
```

Legendary goals involve:

```text
1. Materials.
2. Currencies.
3. Achievements.
4. Collections.
5. Maps.
6. Time-gated requirements.
7. Trading post prices.
8. Goal conflicts.
9. Shared materials across multiple goals.
```

### 3.3 Product Form

```text
Legendary Goal Preview
→ Paid Legendary Report
→ Legendary Planner Pro Subscription
→ Market Radar Add-on
```

### 3.4 Required Capabilities

```text
1. Goal Requirement Graph.
2. Account Owned Graph.
3. Missing Requirement Inference.
4. Do-not-sell policy.
5. TimeGate inference.
6. AcquisitionMethod mapping.
7. GoalPortfolio.
8. CheapPath / FastPath.
9. Market price integration.
10. Paid report and subscription.
```

### 3.5 Required Knowledge Base Domains

```text
docs/knowledge_base/legendary/
├── aurora_guide.md
├── vision_guide.md
├── conflux_guide.md
├── ad_infinitum_guide.md
├── legendary_weapon_guide.md
├── mystic_clover_sources.md
└── do_not_sell_policy.md
```

### 3.6 Core Intelligence Output

Without KB:

```text
You are missing 43 Mystic Clover.
```

With KB + Graph:

```text
Mystic Clover is your current main bottleneck for Aurora. It is also commonly required by other legendary goals. Reserve current related materials, prioritize time-gated acquisition paths this week, and avoid selling supporting materials.
```

This is the difference between a data table and a paid planning product.

---

## 4. Opportunity 3 — Build / Gear Transition Fit

### 4.1 Core User Question

```text
Can my account play this build now, what am I missing, and how much will it cost to switch?
```

### 4.2 Business Nature

This opportunity solves:

```text
Build selection and gear transition cost.
```

Public build websites answer:

```text
How is this build configured?
```

GW2Radar answers:

```text
Is this build suitable for my account?
What gear can I reuse?
What am I missing?
What is the transition cost?
Is there a cheaper alternative?
Is the build still fresh after the latest patch?
```

### 4.3 Product Form

```text
Build Fit Preview
→ Paid Build Transition Report
→ Build Fit Advisor subscription feature
→ Guild Readiness expansion
```

### 4.4 Required Capabilities

```text
1. Build Knowledge Base.
2. Build Requirement Graph.
3. Account Gear Snapshot.
4. GearMatcher.
5. BuildFitScore.
6. GearTransitionCost.
7. BudgetAlternative.
8. PatchFreshnessWarning.
9. Build Fit Report.
```

### 4.5 Required Knowledge Base Domains

```text
docs/knowledge_base/build/
├── build_fit_rules.md
├── gear_transition_rules.md
├── budget_build_rules.md
└── build_source_policy.md
```

### 4.6 Core Intelligence Output

Without KB:

```text
This build requires Berserker gear and you are missing two pieces.
```

With KB + Graph:

```text
Power Reaper is a strong low-friction open-world recovery build for your current account. Your gear match is high, conversion cost is low, and it is more suitable than a high-cost raid-oriented condition build at this stage.
```

This becomes a personal build advisor, not just a build database.

---

## 5. System-Level Relationship

GW2Radar should be understood as a layered intelligence system.

```text
Raw Sources
  ↓
Evidence Store
  ↓
Knowledge Base  ←→  Knowledge Graph
        ↓                ↓
   Explanation       Inference
        ↓                ↓
        Intelligence Engine
                ↓
        Action Recommendation
                ↓
        Paid Report / Dashboard / Subscription
```

### 5.1 Layer Definitions

| Layer | Role | Commercial Value |
|---|---|---|
| Evidence Store | Stores source truth, raw provenance, timestamps, confidence | Trust foundation |
| Knowledge Base | Stores explanations, guides, rules, templates | Makes reports understandable |
| Knowledge Graph | Stores entities, relations, attributes, actions | Enables reasoning |
| Player State Graph | Stores private account state | Enables personalization |
| Inference Engine | Computes gaps, scores, priorities | Creates decision intelligence |
| Action Engine | Generates recommendation actions | Turns analysis into plans |
| Report Engine | Packages advice into Markdown/HTML/PDF/ZIP | Monetization wrapper |
| Dashboard | Keeps advice current | Subscription retention |
| Analytics | Privacy-safe product insights | Commercial optimization |

---

## 6. Knowledge Base vs Knowledge Graph

### 6.1 Knowledge Base

The Knowledge Base stores human-readable and explainable knowledge.

It contains:

```text
1. Guides.
2. Expert rules.
3. FAQ.
4. Summaries.
5. Report templates.
6. Source notes.
7. Strategy explanations.
8. Commercial product language.
```

It answers:

```text
What does this mean?
Why does this matter?
How should the player understand this recommendation?
What should the report say?
```

### 6.2 Knowledge Graph

The Knowledge Graph stores machine-readable relations.

It contains:

```text
1. Entity.
2. Attribute.
3. Relation.
4. Action.
5. Evidence refs.
6. Validity windows.
7. Confidence.
```

It answers:

```text
What exists?
What depends on what?
What does the account own?
What is missing?
Which action advances which goal?
Which build fits this account?
```

### 6.3 Combined Value

```text
Knowledge Base gives explanation.
Knowledge Graph gives computation.
```

Together, they create:

```text
Personalized, explainable, evidence-backed decision intelligence.
```

---

## 7. Where Monetizable Intelligence Comes From

GW2Radar monetizable intelligence comes from seven sources.

### 7.1 Official Facts

Sources:

```text
GW2 API
GW2 Wiki
Official patch notes
Official announcements
```

Value:

```text
High trust, low direct monetization.
```

Official facts provide:

```text
items
recipes
achievements
currencies
prices
account state
API scopes
patch facts
```

### 7.2 Private Player State

Source:

```text
Player-authorized API key.
```

Value:

```text
Very high, because it enables personalization.
```

It provides:

```text
owned materials
wallet
characters
achievements
unlocks
bank
gear
active goals
```

### 7.3 Knowledge Base Explanation

Sources:

```text
official summaries
expert rules
manual notes
structured guides
report templates
```

Value:

```text
Very high, because it explains why.
```

### 7.4 Graph Inference

Sources:

```text
Entity
Attribute
Relation
Action
Player State
```

Value:

```text
Very high, because it computes recommendations.
```

Example:

```text
Goal REQUIRES Item
Account OWNS Item
Required - Owned = Missing
Missing + AcquisitionMethod = Action
```

### 7.5 Expert Rules

Examples:

```text
Returners should recover mobility first.
Active goal materials should be reserved.
Time-gated tasks should be prioritized.
Low-cost builds are better for many returning players.
Market advice must avoid guaranteed-profit language.
```

Value:

```text
Highest strategic value.
```

### 7.6 Market and Patch Changes

Sources:

```text
trading post prices
patch notes
build update timestamps
festival changes
material trends
```

Value:

```text
Subscription-oriented recurring value.
```

### 7.7 Privacy-Safe Aggregated Trends

Allowed:

```text
report type usage
most selected goal categories
common question clusters
feature usage
conversion funnels
anonymous topic trends
```

Forbidden:

```text
specific bank contents
specific account assets
raw account identifiers
API keys
private inventory data
```

Value:

```text
Product optimization, SEO, content planning, conversion improvement.
```

---

## 8. Knowledge Base Collection Strategy

GW2Radar's KB collection is not content scraping. It is:

```text
legal source collection
→ evidence capture
→ summary extraction
→ normalization
→ graph linking
→ rule distillation
→ review
→ publishing
```

---

## 9. Source Levels

### 9.1 Level 0 — Official API / Official Data

Sources:

```text
GW2 API v2
Official announcements
Official patch notes
ArenaNet policy
Official Wiki API docs
```

Use:

```text
highest-confidence facts
API compatibility
Evidence Store
Public Game Graph
Private Player State Graph
```

### 9.2 Level 1 — GW2 Wiki / Public Encyclopedia

Sources:

```text
GW2 Wiki pages
item pages
achievement pages
collection pages
map pages
profession/skill pages
```

Use:

```text
structured summaries
source-linked guide facts
legendary and achievement KB
game system KB
```

### 9.3 Level 2 — Public Build / Guide Sites

Examples:

```text
MetaBattle
Snow Crows
Discretize
GW2Mists
Hardstuck
```

Use:

```text
build name
profession
specialization
game mode
role
difficulty
version
source link
gear requirement summary
```

Do not:

```text
mass-copy full guides
mirror pages
remove attribution
claim ownership
scrape aggressively
```

### 9.4 Level 3 — Community Discussions

Sources:

```text
Reddit
forums
public Discord summaries
YouTube comments
community Q&A
```

Use:

```text
low-confidence topic trends
FAQ discovery
guide gap discovery
creator opportunities
```

Do not use as strong fact without review.

### 9.5 Level 4 — Expert / Internal Knowledge

Sources:

```text
GW2Radar team analysis
manual expert review
user interviews
product feedback
strategy notes
report feedback
```

Use:

```text
expert rules
action ranking
paid report logic
commercial differentiation
```

---

## 10. Knowledge Base Data Models

### 10.1 SourceRegistry

```yaml
SourceRegistry:
  source_id: string
  name: string
  source_type: official_api | official_wiki | public_guide | build_site | community | manual
  base_url: string | null
  allowed_use: api_json | summary_and_reference | manual_note
  crawl_policy: conservative | manual_only | api_only
  rate_limit_policy: low_frequency | gateway_managed | manual
  license_note: string | null
  default_confidence: float
```

### 10.2 KnowledgeArticle

```yaml
KnowledgeArticle:
  kb_id: string
  title: string
  domain: official | game_system | legendary | returner | build | market | guild | creator
  content_type: guide | rule | faq | summary | template | source_note
  summary: string
  body_markdown: string
  source_refs: list[str]
  linked_entities: list[str]
  linked_relations: list[str]
  linked_actions: list[str]
  confidence: float
  review_status: draft | reviewed | deprecated | needs_update | conflict
  last_reviewed_at: datetime | null
  valid_from: datetime | null
  valid_to: datetime | null
```

### 10.3 KnowledgeChunk

```yaml
KnowledgeChunk:
  chunk_id: string
  kb_id: string
  text: string
  token_count: int
  embedding_id: string | null
  linked_entities: list[str]
  linked_actions: list[str]
  source_refs: list[str]
  confidence: float
```

### 10.4 KnowledgeRule

```yaml
KnowledgeRule:
  rule_id: string
  name: string
  domain: returner | legendary | build | market | guild | creator
  condition: string
  recommendation: string
  action_type: string
  priority_delta: float
  explanation_template: string
  evidence_refs: list[str]
  confidence: float
  enabled: bool
```

---

## 11. KB Collection Pipeline

```text
1. Source Registry
2. Ingestion
3. Evidence Capture
4. Extraction
5. Normalization
6. Entity Linking
7. Rule Distillation
8. Review
9. Publish
```

### 11.1 Source Registry

All sources must be registered before use.

### 11.2 Ingestion

Supported modes:

```text
API ingestion
Web summary ingestion
Manual expert note ingestion
Markdown file ingestion
```

### 11.3 Evidence Capture

No important KB item should exist without evidence.

### 11.4 Extraction

Extract:

```text
title
summary
key entities
key actions
conditions
risks
source links
version/date
```

### 11.5 Normalization

Normalize names to graph IDs.

Example:

```text
Mystic Coin → gw2:item:<id>
Aurora → gw2:goal:aurora
Skyscale → gw2:mount:skyscale
Power Reaper → gw2:build:power_reaper_open_world
```

### 11.6 Entity Linking

KB articles must link to graph entities/actions.

### 11.7 Rule Distillation

Convert reviewed knowledge into rules.

Example:

```text
If travel_readiness_score < 0.5
then recommend OpenWorldRecovery and UNLOCK_MOUNT actions.
```

### 11.8 Review

Allowed statuses:

```text
draft
reviewed
deprecated
needs_update
conflict
```

Only reviewed or official high-confidence content may drive high-priority recommendations.

### 11.9 Publish

Published KB can power:

```text
reports
action explanations
RAG/search
SEO
creator intelligence
graph annotations
```

---

## 12. Knowledge Base Directory Structure

Recommended repository layout:

```text
docs/knowledge_base/
├── README.md
├── source_registry/
│   ├── official_sources.md
│   ├── wiki_sources.md
│   ├── build_sources.md
│   └── community_sources.md
├── official/
│   ├── gw2_api_summary.md
│   ├── api_scopes.md
│   ├── api_rate_limit.md
│   └── third_party_policy.md
├── game_systems/
│   ├── legendary_system.md
│   ├── mastery_system.md
│   ├── mount_system.md
│   ├── build_system.md
│   ├── trading_post_system.md
│   └── achievement_collection_system.md
├── legendary/
│   ├── aurora_guide.md
│   ├── vision_guide.md
│   ├── conflux_guide.md
│   ├── ad_infinitum_guide.md
│   ├── legendary_weapon_guide.md
│   ├── mystic_clover_sources.md
│   └── do_not_sell_policy.md
├── returner/
│   ├── returner_7_day_plan.md
│   ├── returner_30_day_plan.md
│   ├── mount_priority.md
│   ├── build_recovery.md
│   └── common_returner_mistakes.md
├── build/
│   ├── build_fit_rules.md
│   ├── gear_transition_rules.md
│   ├── budget_build_rules.md
│   └── build_source_policy.md
├── market/
│   ├── material_retention_rules.md
│   ├── sell_surplus_policy.md
│   ├── market_language_policy.md
│   └── goal_cost_index_rules.md
├── guild/
│   ├── role_coverage_rules.md
│   ├── readiness_report_rules.md
│   └── member_privacy_policy.md
├── creator/
│   ├── topic_opportunity_rules.md
│   ├── guide_gap_rules.md
│   └── community_signal_policy.md
└── report_templates/
    ├── returner_report_template.md
    ├── legendary_report_template.md
    ├── build_fit_report_template.md
    ├── market_report_template.md
    ├── guild_report_template.md
    └── creator_report_template.md
```

---

## 13. KB Code Modules

Recommended implementation:

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

---

## 14. Integration With GW2Radar Repository

The KB design and related commercial intelligence design must be merged into the main GW2Radar repository.

Do not create a separate project.

The repository should have:

```text
one constitution
one ontology
one knowledge base
one graph system
one Codex roadmap
one commercial roadmap
```

---

## 15. Recommended Repository Structure

```text
gw2radar/
├── README.md
├── PROJECT_INDEX.md
├── docs/
│   ├── constitution/
│   ├── product/
│   ├── codex/
│   ├── ontology/
│   ├── knowledge_base/
│   ├── mvp/
│   └── maturity/
├── src/
│   └── gw2radar/
│       ├── kb/
│       ├── graph/
│       ├── inference/
│       ├── ingest/
│       ├── reports/
│       └── api/
└── tests/
```

---

## 16. Three Opportunities and Implementation Modules

| Module | Returner Diagnosis | Legendary Planning | Build Fit | Role |
|---|---:|---:|---:|---|
| Official API | High | High | High | Account/public facts |
| Durable Queue | Support | Support | Support | Reliable sync |
| SecretStore | Support | Support | Support | API key safety |
| Public Static Refresh | Medium | High | High | Items/build resources |
| Knowledge Base | Core | Core | Core | Explanations/rules/templates |
| Knowledge Graph | Core | Core | Core | Object reasoning |
| Player State Graph | Core | Core | Core | Personalization |
| Evidence Store | Core | Core | Core | Trust |
| Action Engine | Core | Core | Core | Recommendations |
| Report Engine | Core | Core | Core | Monetization |
| Market Radar | Support | High | Medium | Price/cost insights |
| Patch Impact | Medium | Medium | High | Version freshness |
| Guild Readiness | Low | Low | High extension | Team product |
| Creator Intelligence | Medium | Medium | Medium | Content product |
| Website/Payment | Commercial | Commercial | Commercial | Monetization |
| Analytics | Commercial | Commercial | Commercial | Optimization |

---

## 17. Codex Task — Merge KB Design Into Main Repository

```text
Current project: GW2Radar

Task:
Merge the knowledge base design, repository integration plan, commercial opportunity model, and KB/graph relationship model into the main GW2Radar repository documentation.

Requirements:
1. Do not modify business logic.
2. Do not implement new features.
3. Create or update docs/knowledge_base/README.md.
4. Add sections explaining:
   - Why GW2Radar needs a Knowledge Base.
   - Knowledge Base vs Knowledge Graph.
   - Evidence Store / KB / Graph / Player State / Inference / Report relationship.
   - Three core business opportunities:
     1. Returner Account Diagnosis
     2. Legendary Planner Pro
     3. Build Fit & Gear Transition Advisor
   - How KB supports each business opportunity.
   - Where monetizable intelligence comes from.
   - Knowledge collection source levels.
   - KB collection pipeline.
   - KB directory structure.
   - KB module design.
   - Repository integration strategy.
5. Create PROJECT_INDEX.md if missing.
6. Link docs/knowledge_base/README.md from PROJECT_INDEX.md and root README.md.
7. Preserve all existing tests.

Hard constraints:
- Do not scrape external content.
- Do not add copyrighted full-text content.
- Do not add private player data to KB.
- Do not add API keys or secrets.
- Do not violate project constitution.

Acceptance:
- docs/knowledge_base/README.md exists.
- PROJECT_INDEX.md links to knowledge base docs.
- root README.md links to PROJECT_INDEX.md or docs index.
- No source code behavior changed.
- pytest remains unaffected.
```

---

## 18. Codex Task — Implement KB Subsystem

```text
Current project: GW2Radar

Task:
Implement the Knowledge Base Collection Subsystem.

Before coding, read:
1. GW2RADAR_PROJECT_CONSTITUTION.md
2. GW2RADAR_API_ACCESS_GOVERNANCE.md
3. GW2_ONTOLOGY_CORE.md
4. ACTION_SCHEMA.md
5. docs/knowledge_base/README.md

Implement:
1. SourceRegistry model.
2. KnowledgeArticle model.
3. KnowledgeChunk model.
4. KnowledgeRule model.
5. KnowledgeRepository.
6. KnowledgeEntityLinker.
7. KnowledgeRuleDistiller.
8. KnowledgeReviewStatus.
9. Markdown-backed KB loader.
10. API endpoints:
   - POST /api/v1/kb/articles
   - GET /api/v1/kb/articles/{kb_id}
   - GET /api/v1/kb/articles?domain=...
   - POST /api/v1/kb/articles/{kb_id}/review
   - POST /api/v1/kb/articles/{kb_id}/deprecate
   - GET /api/v1/kb/search

Hard constraints:
- Do not mass-copy third-party content.
- Preserve source links.
- Store summaries, not full copyrighted pages.
- Mark community-derived claims as low-confidence unless reviewed.
- Do not allow draft KB articles to generate high-priority actions.
- Do not let private player data become public KB content.
- Do not scrape aggressively.
- No proxy pool.
- No IP rotation.

Tests:
- test_kb_article_model.py
- test_kb_repository.py
- test_kb_source_registry.py
- test_kb_entity_linking.py
- test_kb_rule_distillation.py
- test_kb_review_status.py
- test_kb_no_private_data_leakage.py
- test_kb_no_unreviewed_high_priority_action.py
```

---

## 19. Implementation Priorities

Recommended KB implementation order:

```text
KB0 Source Registry + KB Schema
KB1 Official/API KB
KB2 Legendary KB
KB3 Returner KB
KB4 Build KB
KB5 Market KB
KB6 Guild/Creator KB
```

Recommended product dependency:

```text
Returner Diagnosis depends on KB3.
Legendary Planner Pro depends on KB2 and KB5.
Build Fit Advisor depends on KB4.
Market Radar Pro depends on KB5.
Guild Readiness depends on KB4 and KB6.
Creator Intelligence depends on KB3, KB4, KB5, KB6.
```

---

## 20. Final Principle

GW2Radar should not sell data, scraped guides, or automation.

It should sell:

```text
personalized decision intelligence
evidence-backed reports
goal planning
build transition clarity
material retention judgment
team readiness
creator opportunity insight
```

Final statement:

```text
GW2Radar's commercial value comes from converting trusted knowledge and player state into explainable decisions.
```
