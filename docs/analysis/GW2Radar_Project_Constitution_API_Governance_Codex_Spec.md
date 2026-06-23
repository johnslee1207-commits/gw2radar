# GW2Radar Project Constitution & API Access Governance — Codex Development Spec

```text
Document ID: GW2RADAR_PROJECT_CONSTITUTION_AND_API_GOVERNANCE_CODEX_SPEC
Project: GW2Radar
Version: v0.1
Codename: Constitutional Baseline & API Governance Edition
Status: Draft for Codex Implementation
Primary Audience: Codex / AI Agent / Backend Developer / Architecture Reviewer
```

---

## 0. Purpose

This document defines the **constitutional baseline, API access governance, compliance boundaries, data safety rules, and Codex execution constraints** for GW2Radar.

GW2Radar is not a game automation tool. It is a **Guild Wars 2 personal intelligence and decision-support system** built on:

```text
Public GW2 game data
+ Player-authorized account snapshots
+ Game ontology
+ Knowledge graph
+ Goal inference
+ Action recommendation
+ Evidence-backed reporting
```

This document must be treated as a **higher-priority project constraint** than feature requests, implementation shortcuts, or later MVP development tasks.

All future Codex tasks must explicitly comply with this document.

---

## 1. Project Mission

GW2Radar exists to help Guild Wars 2 players answer:

```text
What should I do today?
What should I do this week?
What am I missing for my current goal?
Which materials should I keep?
Which materials may be safely sold?
Which build fits my account?
What did the latest patch change for me?
```

The system should provide:

```text
1. Personal goal planning
2. Legendary crafting gap analysis
3. Account state diagnosis
4. Material retention policy
5. Build fit analysis
6. Market observation
7. Patch impact intelligence
8. Daily / weekly action recommendation
9. Evidence-backed Markdown / HTML reports
```

The system must not become:

```text
1. A game bot
2. A client automation tool
3. A memory-reading overlay
4. A trading bot
5. A gold-selling / RMT tool
6. A power-leveling or boosting tool
7. A proxy-pool scraping system
8. A high-frequency market manipulation tool
```

---

## 2. Constitutional Red Lines

The following rules are non-negotiable.

```text
1. Do not automate gameplay.
2. Do not log into the game client.
3. Do not read game client memory.
4. Do not modify the game client.
5. Do not simulate keyboard, mouse, or player inputs.
6. Do not automate combat, gathering, movement, trading, chat, crafting, or event participation.
7. Do not support RMT, gold selling, account trading, or power leveling.
8. Do not bypass GW2 API rate limits.
9. Do not use IP pools or proxy rotation to evade official API limits.
10. Do not store GW2 API keys in logs or raw evidence payloads.
11. Do not store player API keys in plaintext in production.
12. Do not mix private player account data into the public game knowledge graph.
13. Do not sell, expose, or share player account data.
14. Do not present low-confidence intelligence as certain fact.
15. Do not describe market signals as guaranteed profit.
```

If a requested feature violates any of the above, Codex must refuse to implement it and instead create a safe alternative proposal.

---

## 3. System Identity

GW2Radar is defined as:

```text
Game GitNexus
+ AegisRadar Intelligence Engine
+ Guild Wars 2 Personal Decision Console
```

Its core model is:

```text
Entity
+ Attribute
+ Relation
+ Action
+ Evidence
+ Inference
+ Report
```

The minimum viable intelligence loop is:

```text
Goal
→ Requires
→ Item / Currency / Achievement
→ Account Owns
→ Missing
→ Price / Source
→ Action
→ Recommendation
→ Report
```

---

## 4. Public and Private Graph Separation

The system must maintain strict separation among three graph layers.

### 4.1 Public Game Graph

Contains public, non-user-specific knowledge:

```text
Items
Recipes
Currencies
Achievements
Collections
Build metadata
Maps
Game modes
Trading post public prices
Patch metadata
Public source references
```

### 4.2 Private Player State Graph

Contains player-authorized private data:

```text
Account name / account id
Characters
Inventory
Bank
Material storage
Wallet
Achievement progress
Unlocked masteries
Unlocked mounts
Active personal goals
Personal build state
```

### 4.3 Personal Intelligence Graph

Derived graph combining public knowledge and private player state:

```text
Goal gaps
Missing materials
Reserved materials
Do-not-sell list
Daily action recommendations
Weekly action recommendations
Build fit score
Returner diagnosis
Patch impact for this account
```

### 4.4 Forbidden Data Flow

The following data flows are forbidden:

```text
Private Player State Graph → Public Game Graph
Private player goals → Public market intelligence
Private account inventory → Shared trend dataset
Cross-user comparison without explicit authorization
Training public recommendation models on private player data without explicit consent
```

---

## 5. Player Data Protection Rules

GW2 API keys and account snapshots must be treated as sensitive user data.

### 5.1 API Key Handling

Codex must implement the following rules:

```text
1. Never write API keys to logs.
2. Never store API keys in raw evidence.
3. Never include API keys in reports.
4. Never include API keys in exception messages.
5. Never include API keys in test snapshots.
6. Mask API keys in debugging output.
7. Support user deletion of API key.
8. Support user deletion of account snapshots.
9. Use environment variables or encrypted storage for local development.
10. Use encrypted storage for production.
```

### 5.2 Minimum Permission Principle

The system should only request the minimum GW2 API key permissions required for the selected feature.

Example:

```text
Legendary goal planning:
- account
- characters
- inventories
- wallet
- progression
```

Do not request unrelated permissions unless a feature explicitly requires them.

---

## 6. GW2 API Access Governance

### 6.1 Core Principle

GW2Radar must use the official GW2 API conservatively:

```text
Cache first.
Batch requests.
Deduplicate requests.
Respect rate limits.
Retry with backoff.
Never bypass rate limits.
```

### 6.2 No Proxy Pool in MVP

MVP 0.1 must use:

```text
Single outbound IP
Global token bucket
Endpoint TTL cache
Request deduplication
Refresh queue
429 exponential backoff
```

MVP 0.1 must not implement:

```text
Proxy pools
IP rotation
429-triggered IP switching
High-frequency scraping
Rate-limit evasion
```

### 6.3 Rate Limiter Defaults

Implement conservative limits:

```yaml
gw2_api_rate_limit:
  scope: outbound_ip
  burst_capacity: 250
  refill_rate_per_second: 4
  hard_max_per_minute: 240
```

These values intentionally stay below the commonly cited public API capacity to provide safety margin.

### 6.4 429 Handling

When HTTP 429 is received:

```text
1. Record endpoint, params hash, request id, and timestamp.
2. Do not log API key.
3. Do not switch IP.
4. Apply exponential backoff.
5. Temporarily reduce global request rate.
6. Keep the task in delayed queue.
7. Return refresh_pending or rate_limited_retrying to UI/API callers.
8. Do not present 429 as fatal user-facing failure unless retries are exhausted.
```

### 6.5 Endpoint TTL Policy

MVP default TTL:

```yaml
endpoint_ttl:
  items: 72h
  recipes: 72h
  achievements: 72h
  currencies: 72h
  account: 30m
  characters: 30m
  wallet: 30m
  materials: 30m
  bank: 30m
  account_achievements: 60m
  commerce_prices_goal_items: 30m
  commerce_listings: 60m
```

### 6.6 Refresh Priority

```text
P0: User-triggered refresh for active goal
P1: Account snapshot refresh
P2: Goal-related price refresh
P3: Public static data refresh
P4: Historical market backfill
```

### 6.7 Batch Request Requirement

Codex must avoid N+1 GW2 API requests.

Forbidden pattern:

```text
GET /v2/items/1
GET /v2/items/2
GET /v2/items/3
...
```

Required pattern:

```text
GET /v2/items?ids=1,2,3,...
```

Batch where supported:

```text
items
recipes
achievements
commerce/prices
commerce/listings
skins
traits
skills
```

---

## 7. API Access Architecture

All external GW2 API access must go through a single internal gateway.

Required modules:

```text
src/gw2radar/ingest/gw2_api_client.py
src/gw2radar/ingest/gw2_api_gateway.py
src/gw2radar/ingest/rate_limiter.py
src/gw2radar/ingest/cache_store.py
src/gw2radar/ingest/request_queue.py
src/gw2radar/ingest/refresh_scheduler.py
src/gw2radar/ingest/evidence_writer.py
```

Forbidden:

```text
Business modules directly calling external GW2 API endpoints.
```

Required flow:

```text
Feature module
→ Gw2ApiGateway
→ Cache check
→ Rate limiter
→ Request queue
→ GW2 API client
→ Evidence writer
→ Normalizer
→ Graph builder
→ Inference engine
→ Report generator
```

---

## 8. Evidence Rules

Every important entity, relation, action, and recommendation should be traceable to evidence.

Evidence should include:

```yaml
Evidence:
  evidence_id: string
  source_type: gw2_api | wiki | official_news | public_build_site | user_input | mock
  source_url: string | null
  fetched_at: datetime
  raw_hash: string
  payload_ref: string | null
  confidence: float
  license_note: string | null
```

Rules:

```text
1. No important relation without evidence.
2. No strong recommendation from low-confidence evidence.
3. Stale data must be marked stale.
4. Patch-sensitive data must include valid_from / valid_to.
5. Mock evidence must be clearly marked as mock.
```

---

## 9. Entity / Attribute / Relation / Action Baseline

### 9.1 Entity Types

MVP 0.1 must include:

```text
Account
Character
Goal
Item
Material
Currency
Recipe
Achievement
Collection
Task
Action
TradingPostPrice
Source
Evidence
```

Post-MVP extensions:

```text
Profession
Specialization
Build
Skill
Trait
Weapon
Armor
Rune
Sigil
Relic
Map
Patch
Vendor
Event
Raid
Strike
Fractal
WvWObjective
Guild
```

### 9.2 Attribute Categories

Each entity should support structured attributes:

```text
identity
classification
state
economy
progression
gameplay
temporal
evidence
```

### 9.3 Relation Types

MVP relation types:

```text
REQUIRES
CONSUMES
PRODUCES
USED_IN
UNLOCKS
PART_OF
HAS_PRICE
OWNED_BY
MISSING_FOR_GOAL
ADVANCES_GOAL
BLOCKS_GOAL
RESERVED_FOR_GOAL
```

Post-MVP relation types:

```text
RECOMMENDED_FOR
ALTERNATIVE_TO
AFFECTED_BY_PATCH
COUNTERED_BY
SOLD_BY
LOCATED_IN
CRAFTED_BY
HAS_RECIPE
```

### 9.4 Action Types

MVP action types:

```text
FARM
BUY
SELL_SURPLUS
HOLD
RESERVE_FOR_GOAL
CRAFT
EXCHANGE
COMPLETE_ACHIEVEMENT
COMPLETE_COLLECTION_STEP
DO_DAILY
DO_WEEKLY
GENERATE_DAILY_PLAN
GENERATE_WEEKLY_PLAN
```

Post-MVP action types:

```text
SWITCH_BUILD
CRAFT_GEAR
BUY_GEAR
USE_ALTERNATIVE_BUILD
VERIFY_BUILD_UPDATED
CHECK_PATCH
WATCH_PRICE
WAIT_TO_BUY
DIAGNOSE_RETURNER_STATUS
RECOMMEND_NEXT_GOAL
```

---

## 10. Action Recommendation Boundary

Actions are recommendations only.

Allowed:

```text
Suggest farming
Suggest holding material
Suggest selling surplus
Suggest buying missing item
Suggest completing achievement
Suggest doing daily/weekly
Suggest crafting
Suggest checking patch
Suggest switching build
Generate report
```

Forbidden:

```text
Auto-execute buy/sell
Auto-craft
Auto-farm
Auto-complete event
Auto-control character
Auto-send chat
Auto-interact with game client
```

Every Action must include:

```yaml
Action:
  action_id: string
  action_type: enum
  title: string
  description: string
  target_entity_id: string | null
  target_goal_id: string | null
  preconditions: list
  expected_outputs: list
  costs: object
  constraints: object
  priority_score: float
  urgency: low | medium | high
  reason_codes: list
  evidence_refs: list
  explanation: string
```

---

## 11. Market Intelligence Boundary

GW2Radar may provide market observation, but must not become a market manipulation or automated trading tool.

Allowed phrasing:

```text
Consider holding this material.
This item is required by your active goal.
This price is above recent average.
This material appears safe to sell in surplus quantity.
This item may be worth watching.
```

Forbidden phrasing:

```text
Guaranteed profit.
Must buy now.
Sure win.
Exploit this price.
Automated arbitrage.
Market manipulation opportunity.
```

Allowed market features:

```text
Goal material price monitoring
Legendary cost trend
Do-not-sell list
Surplus material estimate
Watchlist
Cost index
```

Forbidden market features:

```text
Automated trading
Automated order placement
High-frequency arbitrage
Market manipulation coordination
RMT support
```

---

## 12. Third-Party Content Use

GW2Radar may reference public content sources such as:

```text
GW2 Wiki
MetaBattle
Snow Crows
Discretize
GW2Mists
Official forums
Patch notes
Public Reddit discussions
```

Rules:

```text
1. Respect source policies and robots rules.
2. Do not mass-copy full pages.
3. Store structured metadata and links where possible.
4. Store summaries rather than full copyrighted content.
5. Preserve source attribution.
6. Mark uncertain community-derived claims as low-confidence.
7. Avoid presenting community opinion as official fact.
```

---

## 13. MVP 0.1 Development Scope

MVP 0.1 codename:

```text
Legendary Goal Intelligence Edition
```

MVP 0.1 must implement:

```text
1. Project constitution file.
2. Ontology baseline.
3. API gateway skeleton with cache, limiter, and mock client.
4. Evidence model.
5. Entity / relation / action storage.
6. Mock account data.
7. Mock legendary goal, e.g. Aurora.
8. Goal requirement graph.
9. Account-owned graph.
10. Missing requirement inference.
11. HOLD / RESERVE / BUY / FARM / DO_DAILY actions.
12. Markdown report generator.
13. Constitution compliance tests.
```

MVP 0.1 must not implement:

```text
1. Proxy pool.
2. IP rotation.
3. Game client automation.
4. Automatic trading.
5. Full market radar.
6. Full build scraping.
7. RMT support.
8. Production-scale multi-tenant data sharing.
```

---

## 14. Required Repository Files

Codex must create or update:

```text
GW2RADAR_PROJECT_CONSTITUTION.md
GW2RADAR_API_ACCESS_GOVERNANCE.md
docs/ontology/GW2_ONTOLOGY_CORE.md
docs/ontology/ENTITY_TYPES.md
docs/ontology/ATTRIBUTE_SCHEMA.md
docs/ontology/RELATION_TYPES.md
docs/ontology/ACTION_SCHEMA.md
docs/ontology/INFERENCE_RULES.md
docs/mvp/MVP_0_1_LEGENDARY_GOAL.md
docs/mvp/MVP_0_1_CODEX_DEVELOPMENT_SPEC.md
```

Recommended source layout:

```text
src/gw2radar/
├── ingest/
│   ├── gw2_api_client.py
│   ├── gw2_api_gateway.py
│   ├── rate_limiter.py
│   ├── cache_store.py
│   ├── request_queue.py
│   ├── refresh_scheduler.py
│   └── evidence_writer.py
├── ontology/
│   ├── entity_types.py
│   ├── relation_types.py
│   ├── action_types.py
│   └── schemas.py
├── graph/
│   ├── entity_store.py
│   ├── relation_store.py
│   ├── graph_builder.py
│   └── graph_query.py
├── inference/
│   ├── goal_gap.py
│   ├── material_policy.py
│   └── action_ranker.py
├── reports/
│   └── markdown_report.py
└── api/
    └── main.py
```

---

## 15. Constitution Compliance Checklist

Every Codex task must include this checklist.

```text
Constitution Compliance Check:
- [ ] Does not automate gameplay.
- [ ] Does not interact with the game client.
- [ ] Does not read or modify game memory.
- [ ] Does not support RMT, gold selling, account selling, or boosting.
- [ ] Does not bypass GW2 API rate limits.
- [ ] Does not implement proxy pool or IP rotation.
- [ ] All external API calls go through Gw2ApiGateway.
- [ ] API keys are never logged.
- [ ] API keys are not stored in raw evidence.
- [ ] Private player data is separated from public game graph.
- [ ] Important relations include evidence references.
- [ ] Action outputs are recommendations only.
- [ ] Market outputs avoid guaranteed-profit language.
- [ ] Low-confidence data is marked as such.
```

---

## 16. Codex Execution Prompt Template

Use this prompt for future Codex tasks.

```text
You are working on GW2Radar.

Before implementing any feature, read and comply with:

1. GW2RADAR_PROJECT_CONSTITUTION.md
2. GW2RADAR_API_ACCESS_GOVERNANCE.md
3. docs/ontology/GW2_ONTOLOGY_CORE.md
4. docs/ontology/ACTION_SCHEMA.md
5. docs/mvp/MVP_0_1_CODEX_DEVELOPMENT_SPEC.md

This task must not implement:
- gameplay automation
- client memory reading
- game client modification
- automated trading
- RMT support
- proxy pools
- IP rotation
- GW2 API rate-limit evasion
- plaintext API key logging
- private player data leakage into public game graph

Implement the requested feature only if it passes the Constitution Compliance Check.

If the requested feature conflicts with the constitution, stop and produce a safe alternative design.
```

---

## 17. MVP 0.1 Acceptance Criteria

MVP 0.1 is accepted only if all items below pass.

```text
Functional:
- [ ] Mock legendary goal can be created.
- [ ] Mock account state can be loaded.
- [ ] Goal requirements can be represented as graph relations.
- [ ] Owned quantities can be represented as player state.
- [ ] Missing quantities can be inferred.
- [ ] HOLD / RESERVE_FOR_GOAL actions can be generated.
- [ ] BUY or FARM actions can be generated for missing requirements.
- [ ] Markdown report can be generated.

Governance:
- [ ] GW2ApiGateway exists.
- [ ] No business module directly calls external GW2 API.
- [ ] Rate limiter exists.
- [ ] Cache abstraction exists.
- [ ] 429 handling path exists.
- [ ] No proxy pool exists.
- [ ] No IP rotation exists.
- [ ] API key masking test exists.

Evidence:
- [ ] Mock evidence is attached to mock facts.
- [ ] Important relations include evidence ids.
- [ ] Actions include explanation fields.
- [ ] Reports include evidence/source section.

Tests:
- [ ] Ontology enum tests pass.
- [ ] Relation creation tests pass.
- [ ] Goal gap inference tests pass.
- [ ] Action generation tests pass.
- [ ] API key masking tests pass.
- [ ] Constitution compliance tests pass.
```

---

## 18. Development Order

Recommended implementation order:

```text
1. Create constitution and API governance docs.
2. Create ontology enums and schemas.
3. Create evidence schema.
4. Create entity / relation / action persistence.
5. Create GW2ApiGateway skeleton.
6. Create rate limiter and cache interfaces.
7. Create mock account and mock goal fixtures.
8. Implement goal gap inference.
9. Implement action generation.
10. Implement Markdown report.
11. Add compliance tests.
12. Add FastAPI skeleton.
```

---

## 19. Final Rule

If any later requirement conflicts with this document, this document wins.

```text
Constitution first.
Ontology second.
Implementation third.
Commercialization last.
```

GW2Radar must remain a **safe, legal, evidence-backed, player-controlled intelligence system**.
