# GW2Radar MVP 0.2 Returner Account Diagnosis — Codex Development Spec

```text
Document ID: GW2RADAR_MVP_0_2_RETURNER_DIAGNOSIS_CODEX_SPEC
Project: GW2Radar
Version: MVP 0.2
Codename: Returner Account Diagnosis Edition
Chinese Name: 回归玩家账号诊断版
Status: Draft for Codex Implementation
Primary Audience: Codex / Backend Developer / Architecture Reviewer / Product Owner
```

---

## 0. Purpose

This document defines the Codex-ready development specification for **GW2Radar MVP 0.2: Returner Account Diagnosis Edition**.

MVP 0.2 builds on MVP 0.1.

MVP 0.1 implemented the baseline loop:

```text
Goal
→ Requirement
→ Account Owned
→ Missing
→ Action
→ Markdown Report
```

MVP 0.2 extends the system to answer:

```text
I am a returning Guild Wars 2 player. What should I do first?
```

The output is a **Returner Diagnosis Report** with:

```text
1. Account readiness summary
2. Missing expansion / system / unlock analysis
3. Mount and mastery gap analysis
4. Gear and build readiness estimate
5. 7-day returner recovery path
6. 30-day returner recovery path
7. Evidence-backed action recommendations
```

---

## 1. Required Constitutional Compliance

This task must comply with:

```text
GW2RADAR_PROJECT_CONSTITUTION.md
GW2RADAR_API_ACCESS_GOVERNANCE.md
docs/ontology/GW2_ONTOLOGY_CORE.md
docs/ontology/ACTION_SCHEMA.md
docs/mvp/MVP_0_1_CODEX_DEVELOPMENT_SPEC.md
```

Hard constraints:

```text
1. Do not implement gameplay automation.
2. Do not interact with the game client.
3. Do not read or modify game memory.
4. Do not implement automated trading.
5. Do not implement RMT, boosting, or account-sale features.
6. Do not implement proxy pools or IP rotation.
7. Do not bypass GW2 API limits.
8. Do not log API keys.
9. Keep public game graph and private player graph separated.
10. Every important relation and recommendation must include evidence.
11. Actions are recommendations only.
```

---

## 2. Version Positioning

```text
MVP 0.2 = Returner Account Diagnosis Edition
```

Target users:

```text
1. Players returning after months or years.
2. Players with old characters and outdated gear.
3. Players unsure which systems they have unlocked.
4. Players unsure whether to pursue story, mounts, mastery, build, or legendary goals first.
5. Players who want a 7-day or 30-day recovery plan.
```

MVP 0.2 must not attempt to solve every GW2 progression route. It should provide a structured account diagnosis and safe, explainable recommendations.

---

## 3. User Questions

MVP 0.2 must answer:

```text
1. What is my current account readiness level?
2. Which major systems have I unlocked?
3. Which important systems appear missing?
4. Which mounts or travel capabilities should I prioritize?
5. Which masteries or expansions are blocking progress?
6. Which characters look most playable now?
7. Should I focus on Open World, story recovery, build rebuild, or legendary goals?
8. What should I do in the next 7 days?
9. What should I do in the next 30 days?
10. What should I postpone?
```

---

## 4. MVP 0.2 Scope

### 4.1 In Scope

```text
1. ReturnerProfile entity.
2. AccountReadiness entity.
3. Expansion / Mount / Mastery / StoryChapter / UnlockedFeature entities.
4. Readiness score model.
5. Missing unlock inference.
6. Returner action generation.
7. 7-day returner plan.
8. 30-day returner plan.
9. Returner Markdown report.
10. Mock data fixtures.
11. pytest coverage.
12. FastAPI endpoints for returner diagnosis using mock or cached account data.
```

### 4.2 Out of Scope

```text
1. Full market radar.
2. Full build scraping.
3. Full patch parsing.
4. Guild readiness.
5. Creator intelligence.
6. Automatic gameplay.
7. Automated trading.
8. Proxy pool.
9. IP rotation.
10. Full UI polish.
```

---

## 5. New Ontology Delta

### 5.1 New Entity Types

Add these entity types:

```text
Expansion
Mastery
Mount
StoryChapter
UnlockedFeature
AccountReadiness
ReturnerProfile
ReturnerPlan
ReturnerPathStep
```

### 5.2 Entity Descriptions

```yaml
Expansion:
  description: A GW2 expansion or major content pack that gates features.

Mastery:
  description: A mastery line or mastery capability unlocked by the player.

Mount:
  description: A mount or travel capability, such as Raptor, Springer, Skimmer, Jackal, Griffon, Roller Beetle, Warclaw, or Skyscale.

StoryChapter:
  description: A story chapter or episode that may unlock maps, vendors, achievements, or collections.

UnlockedFeature:
  description: A gameplay feature available to the account, such as gliding, mounts, masteries, maps, or major travel systems.

AccountReadiness:
  description: Computed diagnosis of account readiness across major gameplay dimensions.

ReturnerProfile:
  description: Profile describing the player's returner state, inferred account gaps, and likely recovery path.

ReturnerPlan:
  description: A generated 7-day or 30-day plan for account recovery.

ReturnerPathStep:
  description: One step in a returner plan, linked to action, goal, feature, or unlock.
```

---

## 6. New Relation Types

Add these relation types:

```text
ACCOUNT_HAS_UNLOCK
ACCOUNT_MISSING_UNLOCK
FEATURE_REQUIRES_EXPANSION
FEATURE_REQUIRES_STORY
FEATURE_REQUIRES_MASTERY
MOUNT_UNLOCKS_TRAVEL_CAPABILITY
MASTERY_UNLOCKS_CAPABILITY
STORY_UNLOCKS_MAP
ACCOUNT_BLOCKED_BY
ACCOUNT_READY_FOR
RETURNER_PLAN_CONTAINS_STEP
STEP_ADVANCES_READINESS
STEP_UNBLOCKS_FEATURE
```

### 6.1 Relation Examples

```text
Account:Private ACCOUNT_HAS_UNLOCK Mount:Raptor
Account:Private ACCOUNT_MISSING_UNLOCK Mount:Skyscale
Mount:Skyscale MOUNT_UNLOCKS_TRAVEL_CAPABILITY VerticalLongRangeTravel
StoryChapter:X STORY_UNLOCKS_MAP Map:Y
Account:Private ACCOUNT_BLOCKED_BY MissingUnlock:Skyscale
ReturnerPlan:7Day RETURNER_PLAN_CONTAINS_STEP Step:UnlockBasicMount
Step:UnlockBasicMount STEP_ADVANCES_READINESS AccountReadiness:OpenWorld
```

---

## 7. New Action Types

Add these action types:

```text
DIAGNOSE_RETURNER_STATUS
UNLOCK_MOUNT
UNLOCK_MASTERY
UNLOCK_MAP
DO_STORY_STEP
RECOMMEND_RETURNER_PATH
POSTPONE_ADVANCED_GOAL
VERIFY_CHARACTER_PLAYABILITY
REBUILD_BASIC_OPEN_WORLD_BUILD
```

### 7.1 Action Boundary

All actions are recommendations only.

Allowed:

```text
Recommend unlocking a mount.
Recommend completing story step.
Recommend checking mastery.
Recommend using a low-cost open-world build.
Recommend postponing advanced group content.
Generate returner plan.
```

Forbidden:

```text
Auto-play story.
Auto-unlock mount.
Auto-control character.
Auto-join event.
Auto-run route.
Auto-trade.
```

---

## 8. New Attribute Schemas

### 8.1 AccountReadiness

```yaml
AccountReadiness:
  identity:
    entity_id: private:account_readiness:<account_id>
    account_id: string

  dimensions:
    open_world_readiness_score: float
    travel_readiness_score: float
    story_readiness_score: float
    build_readiness_score: float
    gear_readiness_score: float
    group_content_readiness_score: float
    legendary_readiness_score: float
    returner_gap_score: float

  state:
    recommended_primary_path: OpenWorldRecovery | StoryRecovery | BuildRecovery | LegendaryPreparation | GroupContentPreparation
    major_blockers:
      - missing_mount
      - missing_mastery
      - missing_map
      - outdated_build
      - insufficient_gear
      - missing_currency
    playable_now: bool
    recommended_time_horizon: 7d | 30d | 60d

  evidence:
    evidence_refs: list
    confidence: float
```

### 8.2 ReturnerProfile

```yaml
ReturnerProfile:
  identity:
    entity_id: private:returner_profile:<account_id>
    account_id: string

  account_summary:
    character_count: int
    level_80_character_count: int
    professions_available: list
    expansion_ownership_inferred: list
    unlocked_mounts: list
    unlocked_masteries: list
    known_unlocked_maps: list

  diagnosis:
    returner_level: Light | Moderate | Severe
    likely_gap_categories:
      - travel
      - story
      - gear
      - build
      - mastery
      - economy
      - legendary
    recommended_focus: string
```

### 8.3 ReturnerPlan

```yaml
ReturnerPlan:
  identity:
    entity_id: private:returner_plan:<account_id>:7d
    account_id: string
    horizon: 7d | 30d

  plan:
    steps:
      - step_id
    estimated_total_minutes: int
    primary_focus: string
    confidence: float

  explanation:
    summary: string
    warnings: list
```

---

## 9. Readiness Score Model

Implement a simple rule-based scoring model in MVP 0.2.

### 9.1 Score Dimensions

```text
Travel Readiness
Story Readiness
Build Readiness
Gear Readiness
Open World Readiness
Group Content Readiness
Legendary Readiness
Returner Gap Score
```

### 9.2 Recommended Initial Formula

```text
AccountReadinessScore =
  0.20 * travel_readiness
+ 0.15 * story_readiness
+ 0.20 * build_readiness
+ 0.15 * gear_readiness
+ 0.15 * open_world_readiness
+ 0.05 * group_content_readiness
+ 0.10 * legendary_readiness
```

### 9.3 Travel Readiness Heuristic

```text
If account has basic mounts:
  travel_readiness += medium
If account has Skyscale or equivalent high-value travel unlock:
  travel_readiness += high
If no known mount:
  travel_readiness = low
```

### 9.4 Build Readiness Heuristic

MVP 0.2 does not require full Build Fit Graph. Use a simple heuristic:

```text
If account has at least one level 80 character:
  build_readiness += base
If character has plausible equipped gear snapshot:
  build_readiness += medium
If no gear data available:
  mark as unknown
If no level 80 character:
  build_readiness = low
```

### 9.5 Returner Level

```text
Light Returner:
  readiness_score >= 0.70

Moderate Returner:
  0.40 <= readiness_score < 0.70

Severe Returner:
  readiness_score < 0.40
```

---

## 10. Inference Rules

### 10.1 Missing Unlock Inference

```text
If feature is recommended baseline
and account does not have feature
then create ACCOUNT_MISSING_UNLOCK relation.
```

### 10.2 Blocker Inference

```text
If missing unlock blocks recommended path
then create ACCOUNT_BLOCKED_BY relation.
```

### 10.3 Primary Path Recommendation

```text
If travel_readiness is low:
  recommend OpenWorldRecovery / MountUnlock path.

If story_readiness is low and maps are missing:
  recommend StoryRecovery path.

If build_readiness is low but account has level 80 character:
  recommend BuildRecovery path.

If legendary_readiness is low and player has active legendary goal:
  recommend LegendaryPreparation path.

If group_content_readiness is low:
  postpone Raid / Strike / advanced group goals.
```

### 10.4 Postpone Advanced Goal

```text
If group_content_readiness is low
and active goal requires difficult group content
then generate POSTPONE_ADVANCED_GOAL action.
```

### 10.5 7-Day Plan Generation

Generate a short plan with:

```text
1. One high-impact unlock step.
2. One account orientation step.
3. One build recovery step.
4. One low-friction daily routine.
5. One optional goal step.
```

### 10.6 30-Day Plan Generation

Generate a longer plan with:

```text
1. Travel capability improvement.
2. Story / map recovery.
3. Basic build stabilization.
4. Material / wallet recovery.
5. One medium-term goal selection.
6. Optional legendary preparation.
```

---

## 11. Required Modules

Add or update:

```text
src/gw2radar/inference/returner_diagnosis.py
src/gw2radar/inference/readiness_score.py
src/gw2radar/intelligence/returner_report.py
src/gw2radar/reports/returner_markdown_report.py
src/gw2radar/ontology/returner_entities.py
tests/test_returner_diagnosis.py
tests/test_readiness_score.py
tests/test_returner_plan.py
tests/test_returner_report.py
tests/fixtures/mock_returner_account.json
```

---

## 12. API Endpoints

Add FastAPI endpoints.

### 12.1 Diagnose Returner Account

```http
POST /api/v1/returner/diagnose
```

Request:

```json
{
  "account_id": "mock-account",
  "use_mock": true
}
```

Response:

```json
{
  "account_id": "mock-account",
  "readiness_score": 0.56,
  "returner_level": "Moderate",
  "recommended_primary_path": "OpenWorldRecovery",
  "major_blockers": ["missing_skyscale", "outdated_build"],
  "actions": [
    {
      "action_type": "UNLOCK_MOUNT",
      "title": "Prioritize missing travel unlock",
      "priority_score": 0.89,
      "explanation": "Your travel readiness is low, so improving mobility should be prioritized before advanced goals."
    }
  ]
}
```

### 12.2 Generate Returner Report

```http
POST /api/v1/returner/report
```

Request:

```json
{
  "account_id": "mock-account",
  "horizon": "30d",
  "format": "markdown",
  "use_mock": true
}
```

Response:

```json
{
  "report_format": "markdown",
  "report_path": "data/reports/mock-account-returner-report.md",
  "summary": "Returner report generated."
}
```

---

## 13. Report Template

Returner report must include:

```markdown
# GW2Radar Returner Account Diagnosis Report

## 1. Account Readiness Summary

- Overall readiness score:
- Returner level:
- Recommended primary path:
- Main blockers:

## 2. Account Snapshot

- Characters:
- Level 80 characters:
- Available professions:
- Known unlocked mounts:
- Known unlocked masteries:
- Known unlocked maps:

## 3. Missing Unlocks

| Category | Missing | Impact | Recommended Priority |
|---|---|---|---|

## 4. Readiness Scores

| Dimension | Score | Interpretation |
|---|---:|---|

## 5. Recommended 7-Day Recovery Path

1. ...
2. ...
3. ...

## 6. Recommended 30-Day Recovery Path

1. ...
2. ...
3. ...

## 7. Suggested Actions

| Action | Priority | Reason | Evidence |
|---|---:|---|---|

## 8. Postponed Goals

| Goal | Reason |
|---|---|

## 9. Evidence

- Source:
- Fetched at:
- Confidence:
```

---

## 14. Mock Fixture Requirements

Create:

```text
tests/fixtures/mock_returner_account.json
```

Fixture must include:

```json
{
  "account": {
    "id": "mock-account",
    "name": "Mock.1234"
  },
  "characters": [
    {
      "name": "Mock Reaper",
      "profession": "Necromancer",
      "level": 80
    },
    {
      "name": "Mock Guardian",
      "profession": "Guardian",
      "level": 80
    }
  ],
  "unlocks": {
    "mounts": ["Raptor", "Springer"],
    "masteries": ["Gliding Basic"],
    "maps": ["Central Tyria"]
  },
  "goals": [
    {
      "goal_id": "goal:aurora",
      "active": true
    }
  ]
}
```

The fixture must intentionally miss:

```text
Skyscale
Advanced masteries
Some story/map unlocks
Modern build freshness
```

This ensures the returner diagnosis has meaningful gaps.

---

## 15. Testing Requirements

Add pytest cases.

### 15.1 test_readiness_score.py

Must test:

```text
1. Readiness score returns float between 0 and 1.
2. Missing mounts lower travel readiness.
3. Level 80 characters improve build readiness.
4. Missing major systems increase returner gap score.
```

### 15.2 test_returner_diagnosis.py

Must test:

```text
1. Mock account creates ReturnerProfile.
2. Missing unlocks generate ACCOUNT_MISSING_UNLOCK relations.
3. Blockers generate ACCOUNT_BLOCKED_BY relations.
4. Recommended primary path is generated.
```

### 15.3 test_returner_plan.py

Must test:

```text
1. 7-day plan has at least 3 steps.
2. 30-day plan has at least 5 steps.
3. Each plan step links to an Action.
4. Each Action has explanation.
```

### 15.4 test_returner_report.py

Must test:

```text
1. Markdown report can be generated.
2. Report contains readiness summary.
3. Report contains 7-day path.
4. Report contains 30-day path.
5. Report contains evidence section.
```

### 15.5 test_constitution_compliance_returner.py

Must test:

```text
1. No gameplay automation action exists.
2. No automated trading action exists.
3. No proxy pool module is introduced.
4. API keys are not printed in report.
5. Actions are recommendations only.
```

---

## 16. Acceptance Criteria

MVP 0.2 is accepted only if:

```text
Functional:
- [ ] Mock returner account loads.
- [ ] AccountReadiness is computed.
- [ ] ReturnerProfile is generated.
- [ ] Missing unlocks are inferred.
- [ ] Returner primary path is selected.
- [ ] 7-day plan is generated.
- [ ] 30-day plan is generated.
- [ ] Returner Markdown report is generated.

Graph:
- [ ] New entity types are represented.
- [ ] New relation types are represented.
- [ ] Missing unlock relations are created.
- [ ] Blocker relations are created.
- [ ] Plan step relations are created.

Action:
- [ ] UNLOCK_MOUNT action can be generated.
- [ ] UNLOCK_MASTERY action can be generated.
- [ ] DO_STORY_STEP action can be generated.
- [ ] POSTPONE_ADVANCED_GOAL action can be generated.
- [ ] Every action has explanation.
- [ ] Every action has evidence or mock evidence.

Governance:
- [ ] No gameplay automation.
- [ ] No automated trading.
- [ ] No proxy pool.
- [ ] No IP rotation.
- [ ] No API key logging.
- [ ] Private player data remains separate from public graph.

Tests:
- [ ] pytest passes.
- [ ] readiness tests pass.
- [ ] diagnosis tests pass.
- [ ] plan tests pass.
- [ ] report tests pass.
- [ ] constitution compliance tests pass.
```

---

## 17. Codex Implementation Prompt

Use this prompt directly.

```text
Current project: GW2Radar

Implement MVP 0.2: Returner Account Diagnosis Edition.

Before coding, read and comply with:
1. GW2RADAR_PROJECT_CONSTITUTION.md
2. GW2RADAR_API_ACCESS_GOVERNANCE.md
3. docs/ontology/GW2_ONTOLOGY_CORE.md
4. docs/ontology/ACTION_SCHEMA.md
5. docs/mvp/MVP_0_1_CODEX_DEVELOPMENT_SPEC.md

Hard constraints:
- Do not implement gameplay automation.
- Do not interact with the GW2 game client.
- Do not read or modify game memory.
- Do not implement automated trading.
- Do not implement RMT, boosting, or account-sale features.
- Do not implement proxy pools or IP rotation.
- Do not bypass GW2 API rate limits.
- Do not log API keys.
- Keep public game graph and private player graph separated.
- All recommendations must be actions with explanations.
- Important facts must have evidence or mock evidence.

Implement:
1. Returner ontology delta:
   - Expansion
   - Mastery
   - Mount
   - StoryChapter
   - UnlockedFeature
   - AccountReadiness
   - ReturnerProfile
   - ReturnerPlan
   - ReturnerPathStep

2. Relation types:
   - ACCOUNT_HAS_UNLOCK
   - ACCOUNT_MISSING_UNLOCK
   - FEATURE_REQUIRES_EXPANSION
   - FEATURE_REQUIRES_STORY
   - FEATURE_REQUIRES_MASTERY
   - MOUNT_UNLOCKS_TRAVEL_CAPABILITY
   - MASTERY_UNLOCKS_CAPABILITY
   - STORY_UNLOCKS_MAP
   - ACCOUNT_BLOCKED_BY
   - ACCOUNT_READY_FOR
   - RETURNER_PLAN_CONTAINS_STEP
   - STEP_ADVANCES_READINESS
   - STEP_UNBLOCKS_FEATURE

3. Action types:
   - DIAGNOSE_RETURNER_STATUS
   - UNLOCK_MOUNT
   - UNLOCK_MASTERY
   - UNLOCK_MAP
   - DO_STORY_STEP
   - RECOMMEND_RETURNER_PATH
   - POSTPONE_ADVANCED_GOAL
   - VERIFY_CHARACTER_PLAYABILITY
   - REBUILD_BASIC_OPEN_WORLD_BUILD

4. Modules:
   - src/gw2radar/inference/returner_diagnosis.py
   - src/gw2radar/inference/readiness_score.py
   - src/gw2radar/intelligence/returner_report.py
   - src/gw2radar/reports/returner_markdown_report.py

5. Mock fixture:
   - tests/fixtures/mock_returner_account.json

6. API endpoints:
   - POST /api/v1/returner/diagnose
   - POST /api/v1/returner/report

7. Tests:
   - test_readiness_score.py
   - test_returner_diagnosis.py
   - test_returner_plan.py
   - test_returner_report.py
   - test_constitution_compliance_returner.py

Acceptance:
- pytest passes.
- Mock returner account generates AccountReadiness.
- Missing unlocks and blockers are inferred.
- 7-day and 30-day plans are generated.
- Markdown returner report is generated.
- No constitution red line is violated.
```

---

## 18. Development Order

Recommended implementation order:

```text
1. Add ontology enum deltas.
2. Add relation/action enum deltas.
3. Add mock returner fixture.
4. Implement readiness score.
5. Implement missing unlock inference.
6. Implement returner path selection.
7. Implement 7-day and 30-day plan generation.
8. Implement returner markdown report.
9. Add API endpoints.
10. Add pytest coverage.
11. Run constitution compliance tests.
```

---

## 19. Final Rule

MVP 0.2 must remain a diagnosis and planning tool.

```text
It may recommend.
It may explain.
It may generate plans.
It may generate reports.

It must not automate gameplay.
It must not trade.
It must not control the client.
It must not bypass API limits.
```
