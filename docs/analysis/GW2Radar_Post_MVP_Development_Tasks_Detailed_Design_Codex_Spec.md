# GW2Radar Post-MVP Development Tasks & Detailed Design — Codex Spec

```text
Document ID: GW2RADAR_POST_MVP_DEVELOPMENT_TASKS_DETAILED_DESIGN_CODEX_SPEC
Project: GW2Radar
Version: v0.2-planning
Status: Draft for Codex Implementation
Source Baseline: GITNEXUS_MVP_MATURITY_ANALYSIS.md
Date: 2026-06-16
Primary Audience: Codex / Architecture Reviewer / Backend Developer / Product Owner
```

---

## 0. Purpose

This document converts the current GitNexus maturity analysis into a **post-MVP development plan and Codex-ready implementation specification**.

Current baseline:

```text
Overall MVP maturity: 3.55 / 5.0
```

The current implementation is a governed, test-backed MVP substrate. It can generate deterministic legendary-goal intelligence packages from mock data and already contains strong constitutional, ontology, graph, inference, report, export, and API-governance foundations.

However, it is not yet a production account-ingestion system.

---

## 1. Current Maturity Baseline

### 1.1 Current Strengths

```text
1. Constitution / governance baseline is strong.
2. Ontology and semantic schemas are stable for MVP.
3. Mock legendary-goal graph is deterministic and tested.
4. Goal gap inference is implemented.
5. Material policy is conservative and goal-aware.
6. Recommendation actions exist with explanations and reason codes.
7. Evidence quality can downgrade actions and appears in reports.
8. Graph layer separation exists through GraphLayer and repository validation.
9. SQLite persistence exists for MVP graph objects.
10. FastAPI MVP surface exists.
11. Export package generation is deterministic and tested.
12. API gateway/client skeleton exists with safe fake-tested behavior.
13. API key and account snapshot deletion flows exist for MVP.
```

### 1.2 Current Major Gaps

```text
1. Durable refresh queue is not implemented.
2. Queue is currently in-memory only.
3. Production encrypted key storage is not implemented.
4. Real GW2 account ingestion is not implemented.
5. Real public static data refresh worker is not implemented.
6. API gateway is governance-first but not yet productized for real sync.
7. Account snapshot sync pipeline does not yet exist.
8. Public data refresh pipeline does not yet exist.
```

### 1.3 Current Implemented MVP Loop

```text
Mock fixture
→ build_mock_graph
→ GraphData / GraphRepository
→ calculate_goal_gap
→ material_policy
→ generate_actions
→ evidence quality processing
→ Markdown report
→ export package
```

### 1.4 Missing Production Loop

```text
User API Key
→ tokeninfo permission validation
→ durable refresh request
→ Gw2ApiGateway
→ official GW2 API
→ sanitized evidence
→ private player state graph
→ account snapshot sync
→ goal inference
→ action generation
→ report/export
```

---

## 2. Core Architectural Decision

### 2.1 Why P0 Must Be Durable Refresh Queue

The maturity analysis shows that the access/governance path already has:

```text
Gw2ApiGateway
TTL Cache
Token Bucket
Request Queue
GW2ApiClient Skeleton
EvidenceWriter
```

But the request queue is still in-memory.

Before real account sync, public data refresh, or market radar, refresh tasks must survive:

```text
process restart
temporary API failure
429 rate limiting
network timeout
partial processing failure
manual retry
```

Therefore, the next correct implementation priority is:

```text
P0: Durable Refresh Queue
```

Not:

```text
real account sync first
public static refresh first
market radar first
returner diagnosis first
```

---

## 3. Priority Roadmap

Recommended order:

```text
P0: Durable Refresh Queue
P1: Official GW2 API Compatibility Hardening
P2: Account Snapshot Sync Pipeline
P3: Public Static Data Refresh Worker
P4: Returner Account Diagnosis Integration
P5: Production Security Upgrade
```

Alternative fast demo path:

```text
P0: Durable Refresh Queue
P2: Account Snapshot Sync with fake transport only
P4: Returner Diagnosis with mock/synced fake data
P1: Official API hardening
```

---

# P0 — Durable Refresh Queue

## 4. P0 Goal

Implement a SQLite-backed durable refresh queue that persists refresh tasks, retry metadata, state transitions, and sanitized request metadata.

This is the infrastructure layer required before real API ingestion.

---

## 5. P0 Scope

### 5.1 In Scope

```text
1. SQLite refresh_queue table.
2. RefreshQueueStatus enum.
3. RefreshQueuePriority enum.
4. RefreshQueueModel SQLAlchemy model.
5. RefreshQueueRepository.
6. Queue enqueue / list / lease / mark_done / mark_retry / mark_failed operations.
7. Retry metadata persistence.
8. 429 retry metadata persistence.
9. Sanitized endpoint and params hash persistence.
10. Tests for state transitions.
11. Tests proving retry metadata survives repository reload.
12. No background worker unless explicitly scoped.
```

### 5.2 Out of Scope

```text
1. Real GW2 account sync.
2. Public static data refresh worker.
3. Celery / Redis worker.
4. Production encrypted key storage.
5. Multi-node distributed queue.
6. Proxy/IP rotation.
7. Gameplay automation.
8. Automated trading.
```

---

## 6. P0 Detailed Design

### 6.1 RefreshQueueStatus

```python
class RefreshQueueStatus(str, Enum):
    queued = "queued"
    delayed = "delayed"
    processing = "processing"
    succeeded = "succeeded"
    failed = "failed"
```

### 6.2 RefreshQueuePriority

```python
class RefreshQueuePriority(str, Enum):
    p0_user_triggered_active_goal = "P0_USER_TRIGGERED_ACTIVE_GOAL"
    p1_account_snapshot = "P1_ACCOUNT_SNAPSHOT"
    p2_goal_related_price = "P2_GOAL_RELATED_PRICE"
    p3_public_static = "P3_PUBLIC_STATIC"
    p4_market_history_backfill = "P4_MARKET_HISTORY_BACKFILL"
```

### 6.3 RefreshTaskType

```python
class RefreshTaskType(str, Enum):
    account_snapshot_sync = "account_snapshot_sync"
    public_static_refresh = "public_static_refresh"
    goal_price_refresh = "goal_price_refresh"
    market_history_backfill = "market_history_backfill"
```

### 6.4 SQLAlchemy Model

```python
class RefreshQueueModel(Base):
    __tablename__ = "refresh_queue"

    id = Column(String, primary_key=True)
    task_type = Column(String, nullable=False)
    priority = Column(String, nullable=False)
    status = Column(String, nullable=False, index=True)

    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False, default="GET")
    params_hash = Column(String, nullable=True)
    params_json = Column(JSON, nullable=True)

    account_id = Column(String, nullable=True, index=True)
    feature_scope = Column(String, nullable=True)

    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)

    next_attempt_at = Column(DateTime, nullable=True, index=True)
    leased_until = Column(DateTime, nullable=True)
    worker_id = Column(String, nullable=True)

    last_status_code = Column(Integer, nullable=True)
    last_error_code = Column(String, nullable=True)
    last_error_message = Column(String, nullable=True)

    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
```

### 6.5 Pydantic Schemas

```python
class RefreshQueueCreate(BaseModel):
    task_type: RefreshTaskType
    priority: RefreshQueuePriority
    endpoint: str
    method: str = "GET"
    params_json: dict[str, Any] | None = None
    account_id: str | None = None
    feature_scope: str | None = None
    max_attempts: int = 3

class RefreshQueueItem(BaseModel):
    id: str
    task_type: RefreshTaskType
    priority: RefreshQueuePriority
    status: RefreshQueueStatus
    endpoint: str
    method: str
    params_hash: str | None = None
    account_id: str | None = None
    attempt_count: int
    max_attempts: int
    next_attempt_at: datetime | None = None
    leased_until: datetime | None = None
    worker_id: str | None = None
    last_status_code: int | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
```

### 6.6 Repository Interface

```python
class RefreshQueueRepository:
    def enqueue(self, request: RefreshQueueCreate) -> RefreshQueueItem:
        ...

    def list_by_status(self, status: RefreshQueueStatus, limit: int = 100) -> list[RefreshQueueItem]:
        ...

    def lease_next(self, worker_id: str, now: datetime, lease_seconds: int = 60) -> RefreshQueueItem | None:
        ...

    def mark_done(self, task_id: str) -> RefreshQueueItem:
        ...

    def mark_retry(
        self,
        task_id: str,
        status_code: int | None,
        error_code: str,
        error_message: str,
        next_attempt_at: datetime,
    ) -> RefreshQueueItem:
        ...

    def mark_failed(
        self,
        task_id: str,
        status_code: int | None,
        error_code: str,
        error_message: str,
    ) -> RefreshQueueItem:
        ...

    def delete_completed_older_than(self, before: datetime) -> int:
        ...
```

### 6.7 Queue State Rules

```text
queued → processing
processing → succeeded
processing → delayed
processing → failed
delayed → processing after next_attempt_at
processing with expired leased_until → queued or processing can be reclaimed
```

### 6.8 Sanitization Rules

Queue records must not store:

```text
API key
Authorization header
access_token
raw private account payload
proxy URL
outbound IP rotation metadata
game client command
game automation instruction
```

Allowed metadata:

```text
endpoint
method
sanitized params
params hash
account_id
feature_scope
status code
error code
retry timestamp
```

---

## 7. P0 Tests

Required files:

```text
tests/test_refresh_queue_model.py
tests/test_refresh_queue_repository.py
tests/test_refresh_queue_retry_persistence.py
tests/test_refresh_queue_429_persistence.py
tests/test_refresh_queue_no_secret_leakage.py
```

Required cases:

```text
1. enqueue creates queued task.
2. lease_next moves queued task to processing.
3. mark_done moves processing task to succeeded.
4. mark_retry moves processing task to delayed.
5. delayed task becomes available after next_attempt_at.
6. mark_failed records terminal failure.
7. 429 metadata persists across repository reload.
8. params_json does not include API key.
9. endpoint/params hash are sanitized.
10. no proxy/ip rotation fields exist.
```

---

## 8. P0 Acceptance Criteria

```text
Functional:
- [ ] SQLite refresh_queue table exists.
- [ ] RefreshQueueStatus enum exists.
- [ ] RefreshQueuePriority enum exists.
- [ ] RefreshQueueRepository exists.
- [ ] Queue tasks survive repository reload.
- [ ] Retry metadata persists.
- [ ] 429 retry metadata persists.
- [ ] Delayed tasks can be leased after next_attempt_at.

Governance:
- [ ] No API key in queue payload.
- [ ] No Authorization header in queue payload.
- [ ] No proxy fields.
- [ ] No IP rotation fields.
- [ ] No gameplay automation task types.
- [ ] No automated trading task types.

Tests:
- [ ] All queue tests pass.
- [ ] Existing MVP tests still pass.
```

---

# P1 — Official GW2 API Compatibility Hardening

## 9. P1 Goal

Finalize the official-compatible API layer.

This task should implement or verify:

```text
1. OfficialGw2ApiClient.
2. Gw2ApiGateway final behavior.
3. endpoint_schema.
4. tokeninfo.
5. permission_validator.
6. Authorization header only.
7. batch ids support.
8. structured errors.
9. 429 backoff path.
10. sanitized evidence metadata.
```

## 10. Required Tests

```text
tests/test_gw2_api_client_official_contract.py
tests/test_gw2_api_permissions.py
tests/test_gw2_api_batching.py
tests/test_gw2_api_rate_limit_behavior.py
tests/test_gw2_api_key_safety.py
tests/test_gw2_api_evidence_sanitization.py
```

## 11. Acceptance Criteria

```text
- [ ] base_url = https://api.guildwars2.com
- [ ] API version = v2
- [ ] Authorization header is used for private endpoints.
- [ ] API key is not placed in URL.
- [ ] tokeninfo is implemented.
- [ ] scope validator is implemented.
- [ ] P0 official endpoints are covered by tests.
- [ ] ids batching works.
- [ ] 429 does not switch IP.
- [ ] failed official responses do not pollute graph.
```

---

# P2 — Account Snapshot Sync Pipeline

## 12. P2 Goal

Implement real account snapshot ingestion through Gw2ApiGateway and durable queue, using fake transport tests by default.

## 13. Dependency

Requires:

```text
P0 Durable Refresh Queue
P1 Official API Compatibility Hardening
```

## 14. Sync Flow

```text
POST /api/v1/account/sync
→ validate API key in memory or secret store
→ tokeninfo scope validation
→ enqueue account_snapshot_sync task
→ durable queue stores sanitized task
→ drain/worker fetches:
   - /v2/account
   - /v2/characters
   - /v2/account/wallet
   - /v2/account/materials
   - /v2/account/bank
   - /v2/account/achievements
→ write sanitized private evidence metadata
→ write private player state
→ mark task succeeded
```

## 15. Private Layer Rule

All account-derived facts must be written only to:

```text
GraphLayer.private_player_state
```

Inferred recommendations may be written to:

```text
GraphLayer.personal_intelligence
```

Forbidden:

```text
account-derived entity/relation → GraphLayer.public_game
```

## 16. API Endpoints

```http
POST /api/v1/account/sync
GET  /api/v1/account/sync/status
POST /api/v1/account/sync/drain-one
```

`drain-one` is MVP developer utility only.

## 17. Required Tests

```text
tests/test_account_sync_enqueue.py
tests/test_account_sync_scope_validation.py
tests/test_account_sync_private_layer.py
tests/test_account_sync_fake_transport.py
tests/test_account_sync_no_key_leakage.py
```

## 18. Acceptance Criteria

```text
Functional:
- [ ] Account sync task can be enqueued.
- [ ] tokeninfo scope validation runs before private endpoint sync.
- [ ] fake transport can sync mock account data.
- [ ] player state rows are written.
- [ ] private layer is enforced.
- [ ] sync status endpoint works.

Governance:
- [ ] API key not written to queue/evidence/logs.
- [ ] private data does not enter public graph.
- [ ] failed responses do not create graph facts.
- [ ] no real API key needed in default tests.
```

---

# P3 — Public Static Data Refresh Worker

## 19. P3 Goal

Implement public data refresh for stable public game entities.

## 20. Endpoint Set

```text
GET /v2/items?ids=...
GET /v2/achievements?ids=...
GET /v2/currencies?ids=...
GET /v2/recipes?ids=...
```

## 21. Public Layer Rule

All public static data must be written only to:

```text
GraphLayer.public_game
```

Forbidden:

```text
public static refresh → GraphLayer.private_player_state
```

## 22. Batch Strategy

```text
1. Deduplicate ids.
2. Sort ids for stable cache key.
3. Chunk ids if needed.
4. Persist one evidence record per official response.
5. Persist entities with source evidence refs.
6. Avoid N+1 calls.
```

## 23. Tests

```text
tests/test_public_static_refresh_enqueue.py
tests/test_public_static_refresh_batching.py
tests/test_public_static_refresh_public_layer.py
tests/test_public_static_refresh_evidence.py
tests/test_public_static_refresh_cache.py
```

## 24. Acceptance Criteria

```text
- [ ] public_static_refresh task can be enqueued.
- [ ] batch item refresh works using fake transport.
- [ ] public entities are written to public_game layer.
- [ ] evidence metadata is sanitized and linked.
- [ ] TTL cache prevents duplicate requests.
- [ ] no API key required.
- [ ] no private player state writes.
```

---

# P4 — Returner Account Diagnosis Integration

## 25. P4 Goal

Integrate MVP 0.2 Returner Account Diagnosis with synced or mock account state.

## 26. Dependency

Requires:

```text
P2 Account Snapshot Sync Pipeline
```

May use fake synced data for MVP tests.

## 27. Core Features

```text
1. AccountReadiness.
2. ReturnerProfile.
3. Missing unlock inference.
4. Readiness score.
5. 7-day returner path.
6. 30-day returner path.
7. Returner Markdown Report.
```

## 28. Actions

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

## 29. Acceptance Criteria

```text
- [ ] mock/synced account can generate ReturnerProfile.
- [ ] readiness score computed.
- [ ] missing unlocks inferred.
- [ ] 7-day and 30-day plans generated.
- [ ] all actions have explanations.
- [ ] report generated.
- [ ] no gameplay automation.
```

---

# P5 — Production Security Upgrade

## 30. P5 Goal

Move from in-memory API key lifecycle to production-safe encrypted secret handling.

## 31. Candidate Modes

```text
Mode A: Local-only deployment
- encrypted local key storage
- no SaaS multi-user key storage

Mode B: Hosted SaaS deployment
- encrypted key storage
- user authentication
- key rotation
- delete/export workflows
- audit-safe logging
```

## 32. Required Work

```text
1. SecretStore interface.
2. InMemorySecretStore remains for tests.
3. EncryptedSecretStore implementation.
4. API key deletion flow.
5. Account snapshot deletion extension.
6. audit-safe logs.
```

## 33. Acceptance Criteria

```text
- [ ] API key encrypted at rest in production mode.
- [ ] API key deletion works.
- [ ] key never appears in logs/evidence/reports.
- [ ] tests still use fake keys safely.
```

---

# 34. Risk Register

| Risk | Severity | Mitigation |
|---|---:|---|
| In-memory queue loses retry tasks | High | P0 durable queue |
| Real API sync writes private data into public graph | High | P2 private layer tests |
| API key leakage | High | key safety tests and sanitized evidence |
| 429 retry loop | Medium | durable delayed retry state |
| N+1 public refresh calls | Medium | batch endpoint tests |
| Failed API response pollutes graph | Medium | evidence/write guards |
| Returner diagnosis overclaims certainty | Medium | confidence/evidence labels |
| Production key storage incomplete | Medium | P5 SecretStore |
| Background worker complexity | Medium | defer worker until queue state stable |

---

# 35. Release Gates

## Gate P0

```text
Durable queue implemented and tested.
```

## Gate P1

```text
Official API contract tests pass and tokeninfo permissions are enforced.
```

## Gate P2

```text
Private account snapshot sync works with fake transport and writes only private layer.
```

## Gate P3

```text
Public static refresh works with batch fake transport and writes only public_game layer.
```

## Gate P4

```text
Returner diagnosis works from synced or mock account state.
```

## Gate P5

```text
Production API key storage is encrypted or deployment explicitly remains local-only.
```

---

# 36. Codex Task: P0 Durable Refresh Queue

## 36.1 Codex Prompt

```text
Current project: GW2Radar

Implement P0: Durable Refresh Queue.

Before coding, read and comply with:
1. GW2RADAR_PROJECT_CONSTITUTION.md
2. GW2RADAR_API_ACCESS_GOVERNANCE.md
3. docs/ontology/GW2_ONTOLOGY_CORE.md
4. docs/ontology/ACTION_SCHEMA.md
5. docs/mvp/MVP_0_1_CODEX_DEVELOPMENT_SPEC.md

Context:
Current GitNexus maturity analysis shows that gateway, limiter, queue, client, and evidence writer exist, but the refresh queue is in-memory only. Before real account sync or public data refresh, retry tasks must survive process restarts and have clear state transitions.

Implement:
1. SQLite refresh_queue table.
2. RefreshQueueStatus enum:
   - queued
   - delayed
   - processing
   - succeeded
   - failed

3. RefreshQueuePriority enum:
   - P0_USER_TRIGGERED_ACTIVE_GOAL
   - P1_ACCOUNT_SNAPSHOT
   - P2_GOAL_RELATED_PRICE
   - P3_PUBLIC_STATIC
   - P4_MARKET_HISTORY_BACKFILL

4. RefreshTaskType enum:
   - account_snapshot_sync
   - public_static_refresh
   - goal_price_refresh
   - market_history_backfill

5. RefreshQueueModel SQLAlchemy model.

6. RefreshQueueRepository with:
   - enqueue
   - list_by_status
   - lease_next
   - mark_done
   - mark_retry
   - mark_failed
   - delete_completed_older_than

7. Pydantic schemas:
   - RefreshQueueCreate
   - RefreshQueueItem

8. Tests:
   - tests/test_refresh_queue_model.py
   - tests/test_refresh_queue_repository.py
   - tests/test_refresh_queue_retry_persistence.py
   - tests/test_refresh_queue_429_persistence.py
   - tests/test_refresh_queue_no_secret_leakage.py

Hard constraints:
- Do not implement gameplay automation.
- Do not implement automated trading.
- Do not implement proxy pool.
- Do not implement IP rotation.
- Do not store API keys in queue payload.
- Do not store Authorization headers.
- Do not add fields for proxy URL or outbound IP switching.
- Existing MVP tests must continue to pass.

Acceptance:
- pytest passes.
- refresh tasks survive repository reload.
- 429 retry metadata persists.
- delayed tasks can be re-leased after next_attempt_at.
- no API key appears in queue payload, logs, or evidence.
```

## 36.2 Suggested File Changes

```text
src/gw2radar/ingest/refresh_queue.py
src/gw2radar/ingest/refresh_queue_repository.py
src/gw2radar/ingest/refresh_queue_schemas.py
src/gw2radar/db/models.py
src/gw2radar/db/repository.py
tests/test_refresh_queue_model.py
tests/test_refresh_queue_repository.py
tests/test_refresh_queue_retry_persistence.py
tests/test_refresh_queue_429_persistence.py
tests/test_refresh_queue_no_secret_leakage.py
```

## 36.3 Constitution Compliance Checklist

```text
- [ ] Does not automate gameplay.
- [ ] Does not interact with game client.
- [ ] Does not implement automated trading.
- [ ] Does not implement proxy pool.
- [ ] Does not implement IP rotation.
- [ ] Does not store API key.
- [ ] Does not store Authorization header.
- [ ] Queue task payload is sanitized.
- [ ] 429 retry uses delayed status, not IP switching.
- [ ] Existing governance tests pass.
```

---

# 37. Codex Task: P2 Account Snapshot Sync Pipeline

```text
Current project: GW2Radar

Implement P2: Account Snapshot Sync Pipeline.

Prerequisites:
1. P0 Durable Refresh Queue implemented.
2. P1 Official GW2 API Compatibility Hardening implemented or available with fake transport.

Goal:
Implement account snapshot sync through Gw2ApiGateway and durable refresh queue, using fake transport tests by default.

Implement:
1. Refresh task type: account_snapshot_sync.
2. POST /api/v1/account/sync endpoint.
3. GET /api/v1/account/sync/status endpoint.
4. POST /api/v1/account/sync/drain-one developer endpoint.
5. tokeninfo scope validation before sync.
6. account private endpoint sync:
   - /v2/account
   - /v2/characters
   - /v2/account/wallet
   - /v2/account/materials
   - /v2/account/bank
   - /v2/account/achievements

7. Private player state writes only.
8. Sanitized private evidence metadata.
9. Sync status model.
10. Fake transport tests.

Hard constraints:
- No real API key required in default tests.
- No API key logging.
- No private data written to public_game layer.
- Failed responses must not create graph facts.
- No gameplay automation.
- No proxy/IP rotation.
```

Required tests:

```text
tests/test_account_sync_enqueue.py
tests/test_account_sync_scope_validation.py
tests/test_account_sync_private_layer.py
tests/test_account_sync_fake_transport.py
tests/test_account_sync_no_key_leakage.py
```

---

# 38. Codex Task: P3 Public Static Data Refresh

```text
Current project: GW2Radar

Implement P3: Public Static Data Refresh Worker.

Prerequisites:
1. P0 Durable Refresh Queue implemented.
2. Gw2ApiGateway available.
3. EvidenceWriter available.

Goal:
Implement public static data refresh using official batch endpoints and public_game layer only.

Implement:
1. Refresh task type: public_static_refresh.
2. Public refresh planner for:
   - items
   - achievements
   - currencies
   - recipes

3. Batch endpoint calls through Gw2ApiGateway.
4. TTL cache integration.
5. public_game layer entity writes.
6. Sanitized evidence metadata.
7. Public refresh report.

Hard constraints:
- No API key required.
- No private player state writes.
- No N+1 calls for batchable endpoints.
- No proxy/IP rotation.
- No automated trading.
```

Required tests:

```text
tests/test_public_static_refresh_enqueue.py
tests/test_public_static_refresh_batching.py
tests/test_public_static_refresh_public_layer.py
tests/test_public_static_refresh_evidence.py
tests/test_public_static_refresh_cache.py
```

---

# 39. Final Recommendation

The next Codex task should be:

```text
P0 Durable Refresh Queue
```

Reason:

```text
It is the smallest infrastructure task that unlocks real ingestion while reducing operational risk.
```

Do not start real account sync before P0 is complete.

Do not start market radar before P1/P2/P3 are stable.

Do not start production SaaS mode before P5 security upgrade is complete.

---

# 40. Final Codex Instruction Block

```text
You are working on GW2Radar.

The repository is currently a governed, test-backed MVP substrate with deterministic mock legendary-goal intelligence.

The next correct implementation milestone is P0 Durable Refresh Queue.

Do not implement gameplay automation, automated trading, proxy pools, IP rotation, or rate-limit evasion.

Do not log API keys or store secrets in queue payloads.

Keep public game graph, private player state graph, and personal intelligence graph separated.

Implement the durable queue first, with SQLite persistence, retry state, 429 metadata persistence, sanitized payloads, and full pytest coverage.

After P0 passes, proceed to official API hardening, account snapshot sync, and public static refresh.
```
