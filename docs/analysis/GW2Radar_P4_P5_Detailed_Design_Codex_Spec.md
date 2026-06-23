# GW2Radar P4 & P5 Detailed Design — Codex Development Spec

```text
Document ID: GW2RADAR_P4_P5_DETAILED_DESIGN_CODEX_SPEC
Project: GW2Radar
Version: v0.2-planning
Status: Draft for Codex Implementation
Source Baseline:
  - GITNEXUS_MVP_MATURITY_ANALYSIS.md
  - GW2Radar_Post_MVP_Development_Tasks_Detailed_Design_Codex_Spec.md
Primary Audience:
  - Codex
  - Backend Developer
  - Architecture Reviewer
  - Security Reviewer
  - Product Owner
```

---

## 0. Purpose

This document provides the detailed Codex-ready design specification for:

```text
P4: Returner Account Diagnosis Integration
P5: Production Security Upgrade
```

These two milestones are grouped because P4 uses synced account data to generate player-facing intelligence, while P5 upgrades the sensitive data lifecycle required before any production or hosted deployment.

P4 answers:

```text
I am a returning Guild Wars 2 player. What should I do first?
```

P5 answers:

```text
Can GW2Radar safely store and manage user API keys and account snapshots in a production environment?
```

---

## 1. Baseline and Dependencies

### 1.1 Current Baseline

The current MVP maturity analysis indicates:

```text
Overall MVP maturity: 3.55 / 5.0
```

Already implemented or mature enough for MVP:

```text
1. Constitution and governance baseline.
2. Ontology and semantic schema baseline.
3. Mock legendary-goal graph.
4. Goal gap inference.
5. Material policy.
6. Recommendation action generation.
7. Evidence quality handling.
8. Graph layer separation.
9. SQLite persistence.
10. Markdown reports.
11. Export packages.
12. Safe API gateway/client skeleton.
13. API key delete and account snapshot delete in MVP form.
```

Still missing:

```text
1. Durable refresh queue.
2. Real account snapshot sync pipeline.
3. Production encrypted key storage.
4. Real public static data refresh.
```

### 1.2 Required Prior Milestones

P4 should normally depend on:

```text
P0 Durable Refresh Queue
P1 Official GW2 API Compatibility Hardening
P2 Account Snapshot Sync Pipeline
```

P5 should depend on:

```text
P0 Durable Refresh Queue
P1 Official GW2 API Compatibility Hardening
P2 Account Snapshot Sync Pipeline
```

However, P4 can be implemented and tested with:

```text
mock account state
or
fake synced account state
```

before real API integration is enabled.

### 1.3 Hard Constitutional Constraints

The following must remain true:

```text
1. No gameplay automation.
2. No game client interaction.
3. No memory reading or modification.
4. No automated trading.
5. No RMT support.
6. No proxy pool.
7. No IP rotation.
8. No API rate-limit evasion.
9. No API key logging.
10. No private account data written into the public game graph.
11. All recommendations are advisory only.
12. Important facts and recommendations must be evidence-backed.
```

---

# Part A — P4 Returner Account Diagnosis Integration

---

## 2. P4 Version Positioning

```text
Milestone: P4
Name: Returner Account Diagnosis Integration
Chinese Name: 回归玩家账号诊断集成
Primary Goal:
  Use mock/synced account state to generate a structured returner diagnosis,
  readiness scores, missing unlock analysis, 7-day plan, 30-day plan,
  and a Markdown report.
```

P4 must convert account state into user-facing intelligence.

It must not merely display account data.

---

## 3. P4 User Questions

P4 must answer:

```text
1. I have not played GW2 for months or years. What should I do first?
2. What is my current account readiness level?
3. Which major systems have I unlocked?
4. Which important unlocks appear missing?
5. Which mounts, maps, masteries, or story systems should I prioritize?
6. Which characters look playable now?
7. Should I focus on open world, story recovery, build recovery, legendary preparation, or group content?
8. What should I do over the next 7 days?
9. What should I do over the next 30 days?
10. What advanced goals should I postpone?
```

---

## 4. P4 Scope

### 4.1 In Scope

```text
1. AccountReadiness entity.
2. ReturnerProfile entity.
3. ReturnerPlan entity.
4. ReturnerPathStep entity.
5. Missing unlock inference.
6. Readiness score model.
7. Returner primary path selection.
8. 7-day plan generation.
9. 30-day plan generation.
10. Returner action generation.
11. Returner Markdown report.
12. FastAPI endpoints for diagnosis and report.
13. Tests with mock or fake synced account state.
```

### 4.2 Out of Scope

```text
1. Full Build Fit Graph.
2. Full Market Radar.
3. Full Patch Impact Radar.
4. Guild readiness.
5. Creator intelligence.
6. Gameplay automation.
7. Automatic route running.
8. Automated trading.
9. Production encrypted key storage, which belongs to P5.
```

---

## 5. P4 Ontology Delta

### 5.1 New Entity Types

Add or verify:

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
ReadinessDimension
ReturnerBlocker
```

### 5.2 Entity Descriptions

```yaml
Expansion:
  description: A GW2 expansion or major content pack that gates features.

Mastery:
  description: A mastery line or specific mastery capability.

Mount:
  description: A travel capability such as Raptor, Springer, Skimmer, Jackal, Griffon, Roller Beetle, Warclaw, or Skyscale.

StoryChapter:
  description: A story chapter or episode that may unlock maps, vendors, currencies, achievements, or collections.

UnlockedFeature:
  description: Any account-level gameplay feature available to the player.

AccountReadiness:
  description: Computed readiness profile across travel, story, build, gear, group content, and legendary preparation.

ReturnerProfile:
  description: High-level diagnosis of the player's returner state and likely recovery route.

ReturnerPlan:
  description: Generated 7-day or 30-day recovery plan.

ReturnerPathStep:
  description: A step in the returner recovery plan linked to an Action and evidence.

ReadinessDimension:
  description: One scoring dimension in the readiness model.

ReturnerBlocker:
  description: A missing feature or low-readiness dimension blocking recommended progression.
```

---

## 6. P4 Relation Delta

Add or verify these relation types:

```text
ACCOUNT_HAS_UNLOCK
ACCOUNT_MISSING_UNLOCK
FEATURE_REQUIRES_EXPANSION
FEATURE_REQUIRES_STORY
FEATURE_REQUIRES_MASTERY
FEATURE_REQUIRES_MAP
MOUNT_UNLOCKS_TRAVEL_CAPABILITY
MASTERY_UNLOCKS_CAPABILITY
STORY_UNLOCKS_MAP
ACCOUNT_BLOCKED_BY
ACCOUNT_READY_FOR
ACCOUNT_NOT_READY_FOR
RETURNER_PLAN_CONTAINS_STEP
STEP_ADVANCES_READINESS
STEP_UNBLOCKS_FEATURE
STEP_POSTPONES_GOAL
ACTION_RECOMMENDED_FOR_RETURNER
```

### 6.1 Relation Examples

```text
Account:Private ACCOUNT_HAS_UNLOCK Mount:Raptor
Account:Private ACCOUNT_MISSING_UNLOCK Mount:Skyscale
Mount:Skyscale MOUNT_UNLOCKS_TRAVEL_CAPABILITY LongRangeVerticalTravel
Mastery:Gliding MAStERY_UNLOCKS_CAPABILITY BasicGliding
StoryChapter:PathOfFire_Intro STORY_UNLOCKS_MAP CrystalOasis
Account:Private ACCOUNT_BLOCKED_BY ReturnerBlocker:MissingTravelUnlock
ReturnerPlan:7Day RETURNER_PLAN_CONTAINS_STEP Step:StabilizeOpenWorldBuild
Step:UnlockTravelFeature STEP_ADVANCES_READINESS ReadinessDimension:Travel
```

---

## 7. P4 Action Delta

Add or verify:

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
SELECT_PRIMARY_RECOVERY_PATH
GENERATE_7_DAY_RETURNER_PLAN
GENERATE_30_DAY_RETURNER_PLAN
```

### 7.1 Action Boundary

Allowed:

```text
Recommend unlocking a mount.
Recommend completing a story step.
Recommend checking or rebuilding a build.
Recommend doing open-world recovery content.
Recommend postponing advanced group content.
Generate a 7-day plan.
Generate a 30-day plan.
Generate a report.
```

Forbidden:

```text
Auto-play story.
Auto-unlock mount.
Auto-control character.
Auto-run map route.
Auto-join group.
Auto-trade.
Auto-craft.
```

---

## 8. P4 Data Models

### 8.1 AccountReadiness

```python
class AccountReadiness(BaseModel):
    account_id: str

    open_world_readiness_score: float
    travel_readiness_score: float
    story_readiness_score: float
    build_readiness_score: float
    gear_readiness_score: float
    group_content_readiness_score: float
    legendary_readiness_score: float
    returner_gap_score: float
    overall_readiness_score: float

    returner_level: Literal["Light", "Moderate", "Severe"]
    recommended_primary_path: Literal[
        "OpenWorldRecovery",
        "StoryRecovery",
        "BuildRecovery",
        "LegendaryPreparation",
        "GroupContentPreparation",
    ]

    major_blockers: list[str]
    playable_now: bool
    confidence: float
    evidence_refs: list[str]
```

### 8.2 ReturnerProfile

```python
class ReturnerProfile(BaseModel):
    account_id: str

    character_count: int
    level_80_character_count: int
    professions_available: list[str]
    unlocked_mounts: list[str]
    missing_mounts: list[str]
    unlocked_masteries: list[str]
    missing_mastery_categories: list[str]
    known_unlocked_maps: list[str]

    readiness: AccountReadiness
    recommended_focus: str
    warnings: list[str]
    evidence_refs: list[str]
```

### 8.3 ReturnerPlan

```python
class ReturnerPlan(BaseModel):
    account_id: str
    horizon: Literal["7d", "30d"]
    primary_focus: str
    steps: list["ReturnerPathStep"]
    estimated_total_minutes: int | None
    confidence: float
    evidence_refs: list[str]
```

### 8.4 ReturnerPathStep

```python
class ReturnerPathStep(BaseModel):
    step_id: str
    day_or_phase: str
    title: str
    description: str
    action_id: str
    priority_score: float
    estimated_minutes: int | None
    advances_dimension: str
    unblocks_feature: str | None
    evidence_refs: list[str]
    explanation: str
```

---

## 9. P4 Readiness Score Design

### 9.1 Dimensions

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

### 9.2 Overall Score

Initial rule-based formula:

```text
overall_readiness =
  0.20 * travel_readiness
+ 0.15 * story_readiness
+ 0.20 * build_readiness
+ 0.15 * gear_readiness
+ 0.15 * open_world_readiness
+ 0.05 * group_content_readiness
+ 0.10 * legendary_readiness
```

### 9.3 Returner Level

```text
Light:
  overall_readiness >= 0.70

Moderate:
  0.40 <= overall_readiness < 0.70

Severe:
  overall_readiness < 0.40
```

### 9.4 Travel Readiness

```text
If account has no known mount:
  travel_readiness = 0.10

If account has basic mounts:
  travel_readiness = 0.45 to 0.60

If account has multiple mounts but no high-value long-range travel:
  travel_readiness = 0.65

If account has Skyscale or equivalent high-value travel:
  travel_readiness = 0.85 to 1.00
```

### 9.5 Build Readiness

P4 uses a simple heuristic, not full Build Fit Graph.

```text
If no level 80 character:
  build_readiness = 0.10

If at least one level 80 character exists:
  build_readiness >= 0.40

If level 80 character has plausible gear snapshot:
  build_readiness >= 0.60

If build freshness is unknown:
  add warning rather than overclaim.
```

### 9.6 Group Content Readiness

```text
If account has low build_readiness:
  group_content_readiness <= 0.30

If account has no clear support/DPS build:
  group_content_readiness <= 0.40

If user preference avoids group content:
  recommendation should not prioritize group content.
```

### 9.7 Legendary Readiness

Use existing MVP 0.1 goal gap inference if active legendary goal exists.

```text
If active legendary goal exists and major gaps are known:
  legendary_readiness = function(progress, blocker count, gold/material gap)

If no active legendary goal:
  legendary_readiness = unknown or low-priority, not failed.
```

---

## 10. P4 Inference Rules

### 10.1 Missing Unlock Inference

```text
If baseline feature is recommended
and account does not have feature
then create ACCOUNT_MISSING_UNLOCK.
```

### 10.2 Blocker Inference

```text
If missing unlock blocks recommended path
then create ACCOUNT_BLOCKED_BY.
```

### 10.3 Primary Path Selection

```text
If travel_readiness is low:
  recommended_primary_path = OpenWorldRecovery

Else if story_readiness is low:
  recommended_primary_path = StoryRecovery

Else if build_readiness is low:
  recommended_primary_path = BuildRecovery

Else if active legendary goal exists and legendary_readiness is moderate:
  recommended_primary_path = LegendaryPreparation

Else if group_content_readiness is high:
  recommended_primary_path = GroupContentPreparation

Else:
  recommended_primary_path = OpenWorldRecovery
```

### 10.4 Postpone Advanced Goal

```text
If group_content_readiness is low
and active goal requires advanced group content
then generate POSTPONE_ADVANCED_GOAL action.
```

### 10.5 7-Day Plan Generation

Generate a short plan with:

```text
1. One account orientation step.
2. One travel or map unlock step.
3. One basic build recovery step.
4. One low-friction daily routine.
5. One optional active-goal step.
```

### 10.6 30-Day Plan Generation

Generate a broader plan with:

```text
1. Travel capability improvement.
2. Story / map recovery.
3. Basic build stabilization.
4. Material / wallet recovery.
5. One medium-term goal selection.
6. Optional legendary preparation.
```

### 10.7 Evidence and Confidence

```text
If source is mock fixture:
  confidence must be marked mock.

If source is official account snapshot:
  confidence is high for raw state.

If source is heuristic inference:
  confidence should be medium unless supported by multiple evidence facts.

If build freshness is unknown:
  state unknown, not outdated.
```

---

## 11. P4 Modules

Add or update:

```text
src/gw2radar/inference/readiness_score.py
src/gw2radar/inference/returner_diagnosis.py
src/gw2radar/inference/returner_plan.py
src/gw2radar/intelligence/returner_service.py
src/gw2radar/reports/returner_markdown_report.py
src/gw2radar/ontology/returner_entities.py
src/gw2radar/api/routes/returner.py
```

---

## 12. P4 API Endpoints

### 12.1 Diagnose Returner Account

```http
POST /api/v1/returner/diagnose
```

Request:

```json
{
  "account_id": "mock-account",
  "use_mock": true,
  "include_7_day_plan": true,
  "include_30_day_plan": true
}
```

Response:

```json
{
  "account_id": "mock-account",
  "overall_readiness_score": 0.56,
  "returner_level": "Moderate",
  "recommended_primary_path": "OpenWorldRecovery",
  "major_blockers": ["missing_high_value_travel", "unknown_build_freshness"],
  "top_actions": [
    {
      "action_type": "UNLOCK_MOUNT",
      "title": "Prioritize travel capability recovery",
      "priority_score": 0.89,
      "explanation": "Travel readiness is low, so mobility recovery should come before advanced goals."
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

## 13. P4 Markdown Report Template

```markdown
# GW2Radar Returner Account Diagnosis Report

## 1. Account Readiness Summary

- Overall readiness score:
- Returner level:
- Recommended primary path:
- Main blockers:
- Confidence:

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

## 9. Evidence and Confidence Notes

- Source:
- Fetched at:
- Confidence:
- Mock / official:
```

---

## 14. P4 Test Plan

Required tests:

```text
tests/test_readiness_score.py
tests/test_returner_diagnosis.py
tests/test_returner_plan.py
tests/test_returner_report.py
tests/test_returner_api.py
tests/test_constitution_compliance_returner.py
```

Test cases:

```text
1. Readiness score returns value between 0 and 1.
2. Missing high-value travel lowers travel readiness.
3. Level 80 characters improve build readiness.
4. Missing unlocks create ACCOUNT_MISSING_UNLOCK relations.
5. Blockers create ACCOUNT_BLOCKED_BY relations.
6. Primary path is selected.
7. 7-day plan has at least 3 steps.
8. 30-day plan has at least 5 steps.
9. Every plan step links to an Action.
10. Every Action has explanation.
11. Markdown report contains readiness summary.
12. Markdown report contains evidence section.
13. No gameplay automation actions exist.
14. No automated trading actions exist.
15. No API key appears in report.
```

---

## 15. P4 Acceptance Criteria

```text
Functional:
- [ ] Mock or synced account can generate ReturnerProfile.
- [ ] AccountReadiness is computed.
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

# Part B — P5 Production Security Upgrade

---

## 16. P5 Version Positioning

```text
Milestone: P5
Name: Production Security Upgrade
Chinese Name: 生产级安全升级
Primary Goal:
  Upgrade API key and private account data handling from MVP in-memory lifecycle
  to production-safe secret storage, deletion, audit-safe logging, and deployment-mode-aware security.
```

P5 should be completed before any hosted SaaS release.

---

## 17. P5 Security Problem Statement

Current MVP uses:

```text
InMemoryApiKeyStore
```

This is acceptable for MVP and tests, but insufficient for production.

Production risks:

```text
1. API key exposure in logs.
2. API key persistence without encryption.
3. Incomplete deletion semantics.
4. Weak audit trail.
5. Ambiguous local vs hosted deployment mode.
6. Private account snapshots retained longer than intended.
7. No secret rotation lifecycle.
8. No explicit encryption boundary.
```

---

## 18. P5 Deployment Modes

P5 must support explicit deployment modes.

### 18.1 Mode A — Local-Only Mode

```text
DeploymentMode: local_only
```

Characteristics:

```text
1. Runs on user's own machine or private server.
2. API keys stored locally only.
3. Encrypted at rest.
4. No multi-user SaaS storage.
5. User can delete all local secrets and snapshots.
```

Recommended for early private use.

### 18.2 Mode B — Hosted SaaS Mode

```text
DeploymentMode: hosted_saas
```

Characteristics:

```text
1. Multi-user hosted environment.
2. Encrypted key storage required.
3. User authentication required.
4. Strong deletion workflow required.
5. Audit-safe logs required.
6. Tenant isolation required.
```

Hosted SaaS mode must not be enabled until P5 acceptance criteria pass.

### 18.3 Mode C — Test Mode

```text
DeploymentMode: test
```

Characteristics:

```text
1. Uses fake keys.
2. Uses InMemorySecretStore.
3. No real API calls by default.
4. Used for pytest.
```

---

## 19. P5 SecretStore Architecture

### 19.1 Interface

Implement:

```python
class SecretStore(Protocol):
    def put_api_key(self, user_id: str, api_key: str, metadata: dict | None = None) -> SecretRecord:
        ...

    def get_api_key(self, user_id: str) -> str | None:
        ...

    def delete_api_key(self, user_id: str) -> bool:
        ...

    def rotate_api_key(self, user_id: str, new_api_key: str) -> SecretRecord:
        ...

    def get_status(self, user_id: str) -> SecretStatus:
        ...
```

### 19.2 Implementations

```text
InMemorySecretStore
EncryptedLocalSecretStore
EncryptedDatabaseSecretStore
```

### 19.3 Store Selection

```python
def build_secret_store(settings: Settings) -> SecretStore:
    if settings.deployment_mode == "test":
        return InMemorySecretStore()
    if settings.deployment_mode == "local_only":
        return EncryptedLocalSecretStore(...)
    if settings.deployment_mode == "hosted_saas":
        return EncryptedDatabaseSecretStore(...)
```

---

## 20. P5 Secret Models

### 20.1 SecretRecord

```python
class SecretRecord(BaseModel):
    user_id: str
    secret_id: str
    key_fingerprint: str
    created_at: datetime
    updated_at: datetime
    last_used_at: datetime | None = None
    storage_backend: str
    encrypted: bool
```

### 20.2 SecretStatus

```python
class SecretStatus(BaseModel):
    user_id: str
    has_api_key: bool
    key_fingerprint: str | None = None
    created_at: datetime | None = None
    last_used_at: datetime | None = None
    storage_backend: str
    encrypted: bool
```

### 20.3 ApiKeyFingerprint

Fingerprint must not reveal key contents.

```text
fingerprint = first_8_chars(sha256(api_key + server_secret))
```

Never use raw API key as identifier.

---

## 21. P5 Encryption Requirements

### 21.1 Minimum Encryption Requirement

Production API keys must be encrypted at rest.

Recommended local approach:

```text
Fernet / AES-GCM based envelope encryption
```

Required:

```text
1. Encryption key must not be hardcoded.
2. Encryption key must be loaded from environment or secure local config.
3. Encrypted payload must include version metadata.
4. Decryption failure must not leak secret material.
5. Key rotation should be supported at interface level.
```

### 21.2 Encrypted Payload Model

```python
class EncryptedSecretPayload(BaseModel):
    version: str
    algorithm: str
    ciphertext: str
    nonce: str | None = None
    created_at: datetime
```

### 21.3 Forbidden

```text
1. Plaintext API key in database.
2. Plaintext API key in logs.
3. Plaintext API key in evidence.
4. Plaintext API key in report.
5. Plaintext API key in queue payload.
6. Hardcoded encryption key.
```

---

## 22. P5 Database Model

For hosted or encrypted database mode:

```python
class SecretModel(Base):
    __tablename__ = "secrets"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=False, index=True)
    secret_type = Column(String, nullable=False)  # gw2_api_key
    key_fingerprint = Column(String, nullable=False, index=True)

    encrypted_payload_json = Column(JSON, nullable=False)
    storage_backend = Column(String, nullable=False)

    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
```

Rules:

```text
1. Soft delete may be used for audit metadata.
2. Encrypted payload must be removed or cryptographically erased on user delete if required.
3. Raw key must never be stored.
```

---

## 23. P5 Account Snapshot Retention Policy

P5 must define account snapshot retention.

### 23.1 Retention Configuration

```yaml
privacy:
  account_snapshot_retention_days: 30
  allow_user_delete_snapshots: true
  allow_user_delete_api_key: true
  delete_exports_on_user_delete: true
```

### 23.2 Deletion Semantics

User deletion must support:

```text
1. Delete API key.
2. Delete account snapshot.
3. Delete private player state.
4. Delete personal intelligence graph for that user.
5. Delete generated reports/exports if configured.
6. Preserve public game graph.
```

### 23.3 Already Existing MVP Basis

Current MVP already includes:

```text
API key delete
Account snapshot delete
```

P5 extends them to encrypted/production storage and stronger retention semantics.

---

## 24. P5 Audit-Safe Logging

Logs may include:

```text
user_id
account_id
task_id
endpoint name
status code
error code
request params hash
key fingerprint
```

Logs must not include:

```text
API key
Authorization header
access_token
raw account payload
raw inventory payload
raw bank payload
```

### 24.1 Log Sanitizer

Implement:

```python
def sanitize_log_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    ...
```

Must redact keys matching:

```text
api_key
access_token
authorization
token
secret
password
```

---

## 25. P5 API Endpoints

### 25.1 Save API Key

```http
POST /api/v1/security/api-key
```

Request:

```json
{
  "api_key": "submitted-securely"
}
```

Response:

```json
{
  "has_api_key": true,
  "key_fingerprint": "abc12345",
  "encrypted": true,
  "storage_backend": "encrypted_local"
}
```

### 25.2 API Key Status

```http
GET /api/v1/security/api-key/status
```

Response:

```json
{
  "has_api_key": true,
  "key_fingerprint": "abc12345",
  "created_at": "2026-06-16T00:00:00Z",
  "last_used_at": "2026-06-16T01:00:00Z",
  "encrypted": true
}
```

### 25.3 Delete API Key

```http
DELETE /api/v1/security/api-key
```

Response:

```json
{
  "deleted": true
}
```

### 25.4 Delete Private Account Data

```http
DELETE /api/v1/security/private-data
```

Request:

```json
{
  "delete_api_key": true,
  "delete_account_snapshot": true,
  "delete_private_player_state": true,
  "delete_personal_intelligence": true,
  "delete_exports": true
}
```

Response:

```json
{
  "api_key_deleted": true,
  "account_snapshot_deleted": true,
  "private_player_state_deleted": true,
  "personal_intelligence_deleted": true,
  "exports_deleted": true
}
```

---

## 26. P5 Modules

Add or update:

```text
src/gw2radar/security/secret_store.py
src/gw2radar/security/in_memory_secret_store.py
src/gw2radar/security/encrypted_local_secret_store.py
src/gw2radar/security/encrypted_database_secret_store.py
src/gw2radar/security/crypto.py
src/gw2radar/security/log_sanitizer.py
src/gw2radar/security/privacy_delete.py
src/gw2radar/api/routes/security.py
src/gw2radar/db/models.py
```

---

## 27. P5 Tests

Required tests:

```text
tests/test_secret_store_interface.py
tests/test_encrypted_local_secret_store.py
tests/test_encrypted_database_secret_store.py
tests/test_secret_store_no_plaintext.py
tests/test_api_key_fingerprint.py
tests/test_log_sanitizer.py
tests/test_security_api_routes.py
tests/test_private_data_delete.py
tests/test_production_mode_requires_encryption.py
tests/test_constitution_compliance_security.py
```

Test cases:

```text
1. SecretStore can save and retrieve key.
2. InMemorySecretStore works only in test mode.
3. EncryptedLocalSecretStore stores encrypted payload.
4. EncryptedDatabaseSecretStore stores encrypted payload.
5. Raw API key does not appear in DB row.
6. Raw API key does not appear in logs.
7. Raw API key does not appear in evidence.
8. Fingerprint is stable but non-reversible.
9. Delete API key removes usable secret.
10. Delete private data removes private graph data.
11. Public game graph remains after private delete.
12. Production mode refuses plaintext store.
13. Hosted SaaS mode requires encrypted store.
```

---

## 28. P5 Acceptance Criteria

```text
Functional:
- [ ] SecretStore interface exists.
- [ ] InMemorySecretStore remains for tests.
- [ ] EncryptedLocalSecretStore exists.
- [ ] EncryptedDatabaseSecretStore exists or is stubbed with explicit NotImplemented for unsupported mode.
- [ ] API key save/status/delete endpoints exist.
- [ ] Private data delete endpoint exists.
- [ ] Account snapshot delete integrates with existing repository deletion.

Security:
- [ ] API key encrypted at rest in production mode.
- [ ] API key never appears in logs.
- [ ] API key never appears in evidence.
- [ ] API key never appears in reports.
- [ ] API key never appears in queue payload.
- [ ] Production mode refuses plaintext store.
- [ ] Fingerprint is non-reversible.

Privacy:
- [ ] User can delete API key.
- [ ] User can delete account snapshot.
- [ ] User can delete private player state.
- [ ] User can delete personal intelligence graph.
- [ ] Public game graph is preserved.

Tests:
- [ ] secret store tests pass.
- [ ] encryption tests pass.
- [ ] log sanitizer tests pass.
- [ ] privacy deletion tests pass.
- [ ] constitution compliance tests pass.
```

---

# Part C — Combined P4/P5 Integration Rules

---

## 29. P4/P5 Interaction

P4 must use P5 security interfaces when available.

### 29.1 Before P5

P4 may operate on:

```text
mock account state
fake synced account state
in-memory key lifecycle
```

### 29.2 After P5

P4 must access API keys only through:

```text
SecretStore
```

P4 must not access:

```text
raw environment variables directly
raw DB secret rows directly
plain API key logs
```

### 29.3 P4 Report Privacy

Returner reports must not contain:

```text
API key
account private raw payload
bank raw dump
inventory raw dump
unmasked account identifier if privacy setting disables it
```

Returner reports may contain:

```text
summarized character count
level 80 character count
profession list
known unlocked mounts
missing unlock categories
readiness scores
recommendations
evidence labels
```

---

## 30. Combined Release Gates

### Gate P4

```text
Returner diagnosis works from mock or synced account state and generates evidence-backed plans.
```

### Gate P5

```text
Production security mode exists and raw API keys cannot leak into DB, logs, evidence, reports, queue, or exports.
```

### Gate P4 + P5 Combined

```text
Returner diagnosis can run in production security mode without exposing API keys or leaking private account data into the public graph.
```

---

## 31. Codex Prompt — P4 Returner Account Diagnosis Integration

```text
Current project: GW2Radar

Implement P4: Returner Account Diagnosis Integration.

Before coding, read and comply with:
1. GW2RADAR_PROJECT_CONSTITUTION.md
2. GW2RADAR_API_ACCESS_GOVERNANCE.md
3. GW2RADAR_POST_MVP_DEVELOPMENT_TASKS_DETAILED_DESIGN_CODEX_SPEC.md
4. GW2Radar_MVP_0_2_Returner_Diagnosis_Codex_Spec.md
5. docs/ontology/GW2_ONTOLOGY_CORE.md
6. docs/ontology/ACTION_SCHEMA.md

Prerequisites:
- P0 Durable Refresh Queue should be available.
- P1/P2 account snapshot path may be real or fake transport.
- If P5 is not complete, use mock/fake account state and existing in-memory key lifecycle.

Implement:
1. AccountReadiness model.
2. ReturnerProfile model.
3. ReturnerPlan model.
4. ReturnerPathStep model.
5. readiness_score.py.
6. returner_diagnosis.py.
7. returner_plan.py.
8. returner_service.py.
9. returner_markdown_report.py.
10. API routes:
   - POST /api/v1/returner/diagnose
   - POST /api/v1/returner/report

11. Ontology deltas:
   - Expansion
   - Mastery
   - Mount
   - StoryChapter
   - UnlockedFeature
   - AccountReadiness
   - ReturnerProfile
   - ReturnerPlan
   - ReturnerPathStep

12. Relation deltas:
   - ACCOUNT_HAS_UNLOCK
   - ACCOUNT_MISSING_UNLOCK
   - FEATURE_REQUIRES_EXPANSION
   - FEATURE_REQUIRES_STORY
   - FEATURE_REQUIRES_MASTERY
   - FEATURE_REQUIRES_MAP
   - MOUNT_UNLOCKS_TRAVEL_CAPABILITY
   - MASTERY_UNLOCKS_CAPABILITY
   - STORY_UNLOCKS_MAP
   - ACCOUNT_BLOCKED_BY
   - ACCOUNT_READY_FOR
   - ACCOUNT_NOT_READY_FOR
   - RETURNER_PLAN_CONTAINS_STEP
   - STEP_ADVANCES_READINESS
   - STEP_UNBLOCKS_FEATURE
   - STEP_POSTPONES_GOAL
   - ACTION_RECOMMENDED_FOR_RETURNER

13. Action deltas:
   - DIAGNOSE_RETURNER_STATUS
   - UNLOCK_MOUNT
   - UNLOCK_MASTERY
   - UNLOCK_MAP
   - DO_STORY_STEP
   - RECOMMEND_RETURNER_PATH
   - POSTPONE_ADVANCED_GOAL
   - VERIFY_CHARACTER_PLAYABILITY
   - REBUILD_BASIC_OPEN_WORLD_BUILD
   - SELECT_PRIMARY_RECOVERY_PATH
   - GENERATE_7_DAY_RETURNER_PLAN
   - GENERATE_30_DAY_RETURNER_PLAN

Hard constraints:
- Do not implement gameplay automation.
- Do not interact with the GW2 game client.
- Do not read or modify game memory.
- Do not implement automated trading.
- Do not implement proxy pools or IP rotation.
- Do not log API keys.
- Do not write private account data into public_game graph.
- Every action must be recommendation-only and include explanation.
- Every important relation/action must include evidence or mock evidence.

Tests:
- test_readiness_score.py
- test_returner_diagnosis.py
- test_returner_plan.py
- test_returner_report.py
- test_returner_api.py
- test_constitution_compliance_returner.py

Acceptance:
- pytest passes.
- Mock/synced account can generate ReturnerProfile.
- AccountReadiness is computed.
- 7-day and 30-day plans are generated.
- Returner report is generated.
- No constitution red line is violated.
```

---

## 32. Codex Prompt — P5 Production Security Upgrade

```text
Current project: GW2Radar

Implement P5: Production Security Upgrade.

Before coding, read and comply with:
1. GW2RADAR_PROJECT_CONSTITUTION.md
2. GW2RADAR_API_ACCESS_GOVERNANCE.md
3. GW2RADAR_POST_MVP_DEVELOPMENT_TASKS_DETAILED_DESIGN_CODEX_SPEC.md
4. docs/ontology/GW2_ONTOLOGY_CORE.md
5. docs/ontology/ACTION_SCHEMA.md

Goal:
Move from MVP in-memory API key lifecycle to production-safe secret storage, deletion, audit-safe logging, and deployment-mode-aware security.

Implement:
1. DeploymentMode:
   - test
   - local_only
   - hosted_saas

2. SecretStore interface:
   - put_api_key
   - get_api_key
   - delete_api_key
   - rotate_api_key
   - get_status

3. SecretStore implementations:
   - InMemorySecretStore
   - EncryptedLocalSecretStore
   - EncryptedDatabaseSecretStore or explicit NotImplemented with safe failure

4. Crypto helpers:
   - encrypt_secret
   - decrypt_secret
   - fingerprint_api_key
   - mask_api_key

5. SecretModel SQLAlchemy model if encrypted DB mode is supported.

6. API routes:
   - POST /api/v1/security/api-key
   - GET /api/v1/security/api-key/status
   - DELETE /api/v1/security/api-key
   - DELETE /api/v1/security/private-data

7. Privacy delete service:
   - delete API key
   - delete account snapshot
   - delete private player state
   - delete personal intelligence graph
   - optionally delete exports

8. Log sanitizer:
   - redact api_key
   - redact access_token
   - redact authorization
   - redact token
   - redact secret
   - redact password

Hard constraints:
- Do not store plaintext API keys in production mode.
- Do not log API keys.
- Do not write API keys to evidence.
- Do not write API keys to queue payload.
- Do not write API keys to reports.
- Do not hardcode encryption keys.
- Production mode must refuse plaintext store.
- Hosted SaaS mode must require encrypted store.
- Public game graph must remain after private data deletion.

Tests:
- test_secret_store_interface.py
- test_encrypted_local_secret_store.py
- test_encrypted_database_secret_store.py
- test_secret_store_no_plaintext.py
- test_api_key_fingerprint.py
- test_log_sanitizer.py
- test_security_api_routes.py
- test_private_data_delete.py
- test_production_mode_requires_encryption.py
- test_constitution_compliance_security.py

Acceptance:
- pytest passes.
- API key encrypted at rest in production mode.
- API key never appears in DB plaintext/logs/evidence/reports/queue.
- User can delete API key and private data.
- Public game graph is preserved.
- No constitution red line is violated.
```

---

## 33. Recommended Implementation Order

```text
1. P4 ontology/action/relation deltas.
2. P4 readiness score and mock diagnosis.
3. P4 7-day / 30-day plan generation.
4. P4 report and API routes.
5. P4 tests.

Then:

6. P5 DeploymentMode and SecretStore interface.
7. P5 InMemorySecretStore compatibility.
8. P5 encryption helpers.
9. P5 EncryptedLocalSecretStore.
10. P5 optional EncryptedDatabaseSecretStore.
11. P5 security API routes.
12. P5 privacy delete service.
13. P5 tests.
```

If preparing for hosted SaaS, implement P5 before allowing real-user API keys.

---

## 34. Final Rule

P4 makes GW2Radar useful for returning players.

P5 makes GW2Radar safe enough to handle real user credentials and private account snapshots.

Do not treat P4 as production-ready until P5 security gates pass.

```text
P4 = Intelligence value
P5 = Production trust boundary
```
