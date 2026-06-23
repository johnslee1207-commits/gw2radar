# GW2Radar Product Roadmap v0.1 to v1.0

```text
Document ID: GW2RADAR_PRODUCT_ROADMAP_V0_1_TO_V1_0
Project: GW2Radar
Version: v0.1
Status: Draft for Codex / Product Planning
Primary Audience: Codex / Product Owner / Architecture Reviewer / Backend Developer
```

---

## 0. Purpose

This document defines the staged product and engineering roadmap for **GW2Radar**, from MVP 0.1 to v1.0.

GW2Radar is a **Guild Wars 2 personal intelligence system** built on:

```text
GW2 game ontology
+ public game knowledge graph
+ private player state graph
+ personal intelligence graph
+ evidence-backed action recommendation
```

The roadmap must be interpreted under the project constitution:

```text
1. No gameplay automation.
2. No client memory reading.
3. No automated trading.
4. No RMT support.
5. No API rate-limit evasion.
6. No proxy pool for bypassing limits.
7. No private player data leakage into public graph.
8. Every important recommendation must be explainable and evidence-backed.
```

---

## 1. Roadmap Overview

Recommended version sequence:

```text
MVP 0.1  Legendary Goal Intelligence
MVP 0.2  Returner Account Diagnosis
MVP 0.3  Build Fit Graph
MVP 0.4  Market Radar
MVP 0.5  Patch Impact Radar
MVP 0.6  Achievement & Collection Route Planner
MVP 0.7  Daily / Weekly Intelligent Planner
MVP 0.8  Guild / Static Readiness Console
MVP 0.9  Creator & Community Intelligence Console
v1.0     Personal Game Intelligence Platform
```

Short summary:

```text
0.1: Goal gap
0.2: Returner diagnosis
0.3: Build fit
0.4: Market intelligence
0.5: Patch impact
0.6: Achievement route
0.7: Daily / weekly planner
0.8: Guild readiness
0.9: Creator intelligence
1.0: Full personal intelligence platform
```

---

## 2. Global Development Principles

Each version must expand the system by adding:

```text
1. Product capability
2. Ontology delta
3. Entity / Relation / Action delta
4. Inference rules
5. Evidence rules
6. Report template
7. API / data source plan
8. pytest acceptance tests
9. Constitution compliance checklist
```

Do not implement isolated UI features without extending the underlying graph and inference model.

---

## 3. MVP 0.1 — Legendary Goal Intelligence

### 3.1 Version Positioning

```text
Name: Legendary Goal Intelligence Edition
Chinese Name: 个人传奇目标情报图谱版
Primary Goal: Build the minimal loop from Goal → Requirement → Account Owned → Missing → Action → Report.
```

### 3.2 Core User Questions

```text
What am I missing for Aurora / Vision / Legendary Weapon?
Which materials should I reserve?
Which materials should I not sell?
Which missing items can be bought?
Which missing currencies should be farmed?
What should I do today?
What should I do this week?
```

### 3.3 Core Graphs

```text
Goal Graph
Item Graph
Currency Graph
Achievement Graph
Player State Graph
Action Graph
Evidence Graph
```

### 3.4 Required Features

```text
1. Project constitution and API governance baseline.
2. Entity / Relation / Action / Evidence ontology.
3. Mock account data.
4. Mock legendary goal, for example Aurora.
5. Requirement graph.
6. Owned quantity graph.
7. Missing requirement inference.
8. HOLD / RESERVE / BUY / FARM / DO_DAILY action generation.
9. Markdown report generation.
10. pytest coverage.
```

### 3.5 Non-Goals

```text
No full market radar.
No full build scraping.
No patch parsing.
No guild functionality.
No game automation.
No proxy pool.
No IP rotation.
No automated trading.
```

### 3.6 Acceptance Criteria

```text
- Mock legendary goal can be created.
- Mock account state can be loaded.
- Missing materials and currencies can be inferred.
- Do-not-sell list can be generated.
- Daily and weekly action recommendations can be generated.
- Markdown report can be generated.
- Every action has explanation and evidence reference.
```

---

## 4. MVP 0.2 — Returner Account Diagnosis

### 4.1 Version Positioning

```text
Name: Returner Account Diagnosis Edition
Chinese Name: 回归玩家账号诊断版
Primary Goal: Help returning players understand account readiness, missing unlocks, build readiness, and 7-day / 30-day recovery paths.
```

### 4.2 Core User Questions

```text
I have not played for years. What changed?
Which systems am I missing?
Which mounts and masteries should I unlock first?
Are my characters still usable?
Are my builds or gear outdated?
What should I do in the first 7 days?
What should I do in the first 30 days?
```

### 4.3 New Entity Types

```text
Expansion
Mastery
Mount
StoryChapter
UnlockedFeature
AccountReadiness
ReturnerProfile
ReturnerPlan
```

### 4.4 New Relations

```text
ACCOUNT_HAS_UNLOCK
ACCOUNT_MISSING_UNLOCK
FEATURE_REQUIRES_EXPANSION
MOUNT_UNLOCKS_TRAVEL_CAPABILITY
MASTERY_UNLOCKS_CAPABILITY
STORY_UNLOCKS_MAP
ACCOUNT_BLOCKED_BY
ACCOUNT_READY_FOR
```

### 4.5 New Actions

```text
DIAGNOSE_RETURNER_STATUS
UNLOCK_MOUNT
UNLOCK_MASTERY
UNLOCK_MAP
DO_STORY_STEP
RECOMMEND_RETURNER_PATH
POSTPONE_ADVANCED_GOAL
```

### 4.6 Output Report

```text
Returner Report
├── Account readiness summary
├── Expansion / system ownership
├── Missing mounts
├── Missing masteries
├── Missing maps / story prerequisites
├── Gear and build readiness
├── Recommended playable characters
├── 7-day recovery path
└── 30-day recovery path
```

### 4.7 Acceptance Criteria

```text
- Mock returner profile can be loaded.
- Account readiness score can be computed.
- Missing unlocks can be inferred.
- 7-day returner path can be generated.
- 30-day returner path can be generated.
- Report contains clear explanation and evidence references.
```

---

## 5. MVP 0.3 — Build Fit Graph

### 5.1 Version Positioning

```text
Name: Build Fit Graph Edition
Chinese Name: Build 账号适配图谱版
Primary Goal: Analyze whether public builds fit the player's current account and what conversion cost is required.
```

### 5.2 Core User Questions

```text
Which builds fit my account now?
How much does it cost to switch to this build?
Can I reuse my existing gear?
Which runes, sigils, relics, weapons, or stats am I missing?
Is there a lower-cost alternative?
```

### 5.3 New Entity Types

```text
Build
Profession
Specialization
Skill
Trait
Weapon
Armor
Trinket
Rune
Sigil
Relic
StatCombo
Role
GameMode
BuildSource
BuildVariant
```

### 5.4 New Relations

```text
BUILD_USES_PROFESSION
BUILD_USES_SPECIALIZATION
BUILD_REQUIRES_WEAPON
BUILD_REQUIRES_GEAR_STAT
BUILD_REQUIRES_RUNE
BUILD_REQUIRES_SIGIL
BUILD_REQUIRES_RELIC
BUILD_RECOMMENDED_FOR
BUILD_HAS_ROLE
BUILD_ALTERNATIVE_TO
ACCOUNT_FITS_BUILD
ACCOUNT_MISSING_FOR_BUILD
```

### 5.5 Build Fit Score

Recommended formula:

```text
BuildFitScore =
  0.30 * gear_match
+ 0.20 * unlock_match
+ 0.15 * cost_affordability
+ 0.15 * difficulty_match
+ 0.10 * preferred_mode_match
+ 0.10 * patch_freshness
```

### 5.6 New Actions

```text
SWITCH_BUILD
CRAFT_GEAR
BUY_GEAR
USE_ALTERNATIVE_BUILD
VERIFY_BUILD_UPDATED
POSTPONE_BUILD_TRANSITION
```

### 5.7 Output Report

```text
Build Fit Report
├── Recommended builds
├── Fit score
├── Missing gear
├── Conversion cost
├── Reusable gear
├── Budget alternatives
├── Difficulty warning
└── Patch freshness warning
```

---

## 6. MVP 0.4 — Market Radar

### 6.1 Version Positioning

```text
Name: Market Radar Edition
Chinese Name: 交易所与材料市场情报版
Primary Goal: Provide goal-aware market observation, material retention advice, and surplus sell candidates.
```

### 6.2 Core User Questions

```text
Which goal materials are expensive now?
Which materials should I hold?
Which surplus materials may be safely sold?
How has my legendary goal cost changed?
Which items should I watch?
```

### 6.3 New Entity Types

```text
MarketSnapshot
PricePoint
PriceTrend
ItemWatchlist
GoalCostIndex
MarketSignal
SellCandidate
HoldCandidate
```

### 6.4 New Relations

```text
ITEM_HAS_PRICE_POINT
ITEM_HAS_PRICE_TREND
ITEM_PART_OF_GOAL_COST_INDEX
ITEM_IS_HOLD_CANDIDATE
ITEM_IS_SELL_CANDIDATE
MARKET_SIGNAL_AFFECTS_GOAL
```

### 6.5 New Actions

```text
WATCH_PRICE
HOLD_FOR_GOAL
SELL_SURPLUS
WAIT_TO_BUY
BUY_NOW_LOW_RISK
TRACK_COST_INDEX
```

### 6.6 Market Language Constraint

Allowed:

```text
Consider holding.
This item is required by your active goal.
Price is above recent average.
This material appears safe to sell in surplus quantity.
```

Forbidden:

```text
Guaranteed profit.
Must buy now.
Sure win.
Exploit this.
Automated arbitrage.
```

---

## 7. MVP 0.5 — Patch Impact Radar

### 7.1 Version Positioning

```text
Name: Patch Impact Radar Edition
Chinese Name: 版本补丁影响雷达版
Primary Goal: Analyze patch impact on builds, goals, materials, professions, and the player's current account.
```

### 7.2 Core User Questions

```text
Did this patch affect my main profession?
Are my builds still valid?
Which skills or traits changed?
Should I verify my build?
Did any goal or material become more expensive or less relevant?
```

### 7.3 New Entity Types

```text
Patch
PatchNote
BalanceChange
SkillChange
TraitChange
ItemChange
BuildImpact
MarketImpact
GoalImpact
```

### 7.4 New Relations

```text
PATCH_CHANGES_SKILL
PATCH_CHANGES_TRAIT
PATCH_CHANGES_ITEM
PATCH_AFFECTS_BUILD
PATCH_AFFECTS_GOAL
PATCH_AFFECTS_MARKET_SIGNAL
ACCOUNT_AFFECTED_BY_PATCH
```

### 7.5 New Actions

```text
CHECK_PATCH
VERIFY_BUILD_UPDATED
RECOMPUTE_GOAL_AFTER_PATCH
WATCH_IMPACTED_ITEM
SWITCH_BUILD_IF_NEEDED
```

### 7.6 Impact Propagation

```text
Patch changes Skill/Trait
Build uses Skill/Trait
Account uses Build
=> Account affected by Patch
=> Generate VERIFY_BUILD_UPDATED Action
```

---

## 8. MVP 0.6 — Achievement & Collection Route Planner

### 8.1 Version Positioning

```text
Name: Achievement & Collection Route Planner Edition
Chinese Name: 成就与收藏路线规划版
Primary Goal: Convert complex achievement and collection chains into map-aware executable route plans.
```

### 8.2 Core User Questions

```text
Which collection steps am I missing?
Which steps are in the same map?
Which steps require story prerequisites?
Which steps require group content?
Which steps can I complete today?
```

### 8.3 New Entity Types

```text
AchievementStep
CollectionStep
Route
RouteSegment
MapCluster
Prerequisite
TimeGate
```

### 8.4 New Relations

```text
ACHIEVEMENT_HAS_STEP
COLLECTION_HAS_STEP
STEP_LOCATED_IN_MAP
STEP_REQUIRES_PREREQUISITE
STEP_CAN_BE_GROUPED_WITH
STEP_ADVANCES_GOAL
ROUTE_CONTAINS_STEP
```

### 8.5 New Actions

```text
COMPLETE_STEP
RUN_ROUTE_SEGMENT
UNLOCK_PREREQUISITE
GROUP_STEPS_BY_MAP
POSTPONE_BLOCKED_STEP
```

---

## 9. MVP 0.7 — Daily / Weekly Intelligent Planner

### 9.1 Version Positioning

```text
Name: Daily / Weekly Intelligent Planner Edition
Chinese Name: 每日/每周智能计划版
Primary Goal: Combine goals, market status, achievements, builds, and user time budget into actionable daily and weekly plans.
```

### 9.2 Core User Questions

```text
I only have 30 minutes today. What should I do?
What should I prioritize this week?
Which actions advance multiple goals?
Which actions are time-gated?
Which actions should be delayed?
```

### 9.3 New Entity Types

```text
Plan
DailyPlan
WeeklyPlan
ActionBundle
TimeBudget
PriorityPolicy
UserPreference
```

### 9.4 New Relations

```text
PLAN_CONTAINS_ACTION
ACTION_BUNDLED_WITH
ACTION_COMPETES_WITH
ACTION_REQUIRES_TIME_BUDGET
ACTION_MATCHES_PREFERENCE
```

### 9.5 Action Priority Model

```text
ActionPriority =
  goal_priority
+ missing_criticality
+ time_gate_urgency
+ accessibility
+ low_time_high_gain
+ multi_goal_benefit
+ user_preference_match
- difficulty_penalty
- group_required_penalty
```

---

## 10. MVP 0.8 — Guild / Static Readiness Console

### 10.1 Version Positioning

```text
Name: Guild / Static Readiness Console Edition
Chinese Name: 公会/固定队准备度控制台
Primary Goal: Analyze team role coverage, member readiness, build coverage, and group goal alignment.
```

### 10.2 Core User Questions

```text
Which roles are missing?
Do we have enough Quickness / Alacrity / Healers?
Are members ready for target content?
Which builds are missing?
What should the guild train this week?
```

### 10.3 New Entity Types

```text
Guild
Team
TeamMember
TeamRole
RoleCoverage
TeamGoal
ReadinessScore
ConsentRecord
```

### 10.4 Privacy Rules

```text
Each member must explicitly authorize access.
No unauthorized member data.
No cross-team leakage.
Team reports are visible only to authorized team users.
```

### 10.5 New Relations

```text
TEAM_HAS_MEMBER
MEMBER_HAS_ROLE
TEAM_REQUIRES_ROLE
MEMBER_FITS_ROLE
TEAM_MISSING_ROLE
TEAM_READY_FOR_CONTENT
```

---

## 11. MVP 0.9 — Creator & Community Intelligence Console

### 11.1 Version Positioning

```text
Name: Creator & Community Intelligence Console Edition
Chinese Name: 内容创作者与社区情报版
Primary Goal: Help guide writers, video creators, and community managers identify player pain points and content opportunities.
```

### 11.2 Core User Questions

```text
What are players asking about this week?
Which builds were affected by the latest patch?
Which legendary routes need better guides?
Which returner questions are common?
Which market changes are worth explaining?
```

### 11.3 New Entity Types

```text
CommunitySignal
ContentOpportunity
TopicTrend
QuestionCluster
GuideGap
AudienceSegment
```

### 11.4 New Relations

```text
SIGNAL_SUPPORTS_TOPIC
TOPIC_RELATED_TO_GOAL
TOPIC_RELATED_TO_PATCH
TOPIC_RELATED_TO_BUILD
QUESTION_CLUSTER_INDICATES_GUIDE_GAP
```

### 11.5 Boundary

```text
Do not mass-copy community content.
Do not present third-party content as original.
Store summaries, trends, citations, and links.
Mark uncertain community-derived claims as low-confidence.
```

---

## 12. v1.0 — Personal Game Intelligence Platform

### 12.1 Version Positioning

```text
Name: Personal Game Intelligence Platform
Chinese Name: GW2 个人游戏情报平台
Primary Goal: Deliver a complete personal decision console for GW2 players.
```

### 12.2 Required v1.0 Capabilities

```text
1. Stable account data integration.
2. Game ontology core.
3. Public game knowledge graph.
4. Private player state graph.
5. Personal intelligence graph.
6. Multi-goal planning.
7. Build fit analysis.
8. Market radar.
9. Patch impact radar.
10. Daily / weekly planner.
11. Returner diagnosis.
12. Report system.
13. Web console.
14. Constitution compliance checks.
15. API rate limiting and cache governance.
```

### 12.3 v1.0 Dashboard

The user should see:

```text
1. Active goals
2. Goal progress
3. Today's recommended actions
4. Weekly plan
5. Do-not-sell list
6. Build fit alerts
7. Market watch
8. Patch impact alerts
9. Recommended next goal
```

---

## 13. Version Dependency Graph

```text
MVP 0.1 Goal Graph
  ├── MVP 0.2 Returner Diagnosis
  ├── MVP 0.4 Market Radar
  ├── MVP 0.6 Achievement Route
  └── MVP 0.7 Planner

MVP 0.3 Build Fit
  ├── MVP 0.5 Patch Impact
  ├── MVP 0.7 Planner
  └── MVP 0.8 Guild Readiness

MVP 0.4 Market Radar
  ├── MVP 0.7 Planner
  └── MVP 0.9 Creator Intelligence

MVP 0.5 Patch Impact
  ├── MVP 0.3 Build Update
  ├── MVP 0.4 Market Watch
  └── MVP 0.9 Content Opportunity
```

Recommended full order:

```text
0.1 → 0.2 → 0.3 → 0.4 → 0.5 → 0.6 → 0.7 → 0.8 → 0.9 → 1.0
```

Commercial validation path:

```text
0.1 → 0.2 → 0.3 → paid report validation
```

Senior-player value path:

```text
0.1 → 0.4 → 0.7
```

Guild path:

```text
0.1 → 0.3 → 0.8
```

---

## 14. Standard Deliverables for Each Version

Every version must produce:

```text
1. Product Spec
2. Ontology Delta
3. Entity / Relation / Action Delta
4. Inference Rules
5. API / Data Source Plan
6. Report Template
7. pytest Acceptance Tests
8. Constitution Compliance Check
```

---

## 15. Codex Task Template

Use this template for each version.

```text
Current project: GW2Radar

This task must comply with:
1. GW2RADAR_PROJECT_CONSTITUTION.md
2. GW2RADAR_API_ACCESS_GOVERNANCE.md
3. GW2_ONTOLOGY_CORE.md
4. MVP_0_1_CODEX_DEVELOPMENT_SPEC.md

Implement version: MVP 0.X — <Version Name>

Hard constraints:
1. Do not implement gameplay automation.
2. Do not implement automated trading.
3. Do not implement proxy pools or IP rotation.
4. Do not bypass GW2 API rate limits.
5. Do not log API keys.
6. Keep public graph and private player graph separated.
7. Every important entity, relation, and action must support evidence.
8. Every recommendation action must include explanation.
9. Provide pytest coverage.
10. Output Markdown report template.

Deliverables:
- Product spec
- Ontology delta
- DB schema delta
- Inference rules
- Action generation logic
- Markdown report
- API endpoints
- Tests
- Constitution compliance checklist

Acceptance:
- pytest passes
- mock data runs end-to-end
- report can be generated
- actions are recommendations only
- no API key leakage
- no rate-limit evasion
- no proxy pool
- important conclusions are evidence-backed
```

---

## 16. Recommended Next Step

After MVP 0.1, implement:

```text
MVP 0.2 — Returner Account Diagnosis
```

Reason:

```text
1. Strong commercial value.
2. Clear returner-player pain point.
3. Does not require complex market history.
4. Does not require third-party build scraping.
5. Can be built mostly from official API + account state + graph rules.
6. Suitable for free lead-generation reports or paid detailed reports.
```

---

## 17. Final Rule

GW2Radar must grow by graph domains, not by ad hoc pages.

```text
Goal first.
Account diagnosis second.
Build fit third.
Market fourth.
Patch fifth.
Route sixth.
Planner seventh.
Guild eighth.
Creator ninth.
Platform last.
```
