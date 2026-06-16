# GitNexus MVP Maturity Analysis

Date: 2026-06-16

GitNexus command:

```text
npx gitnexus analyze
```

Index result:

```text
Previous indexed commit: 185533e
Current implementation status: pending post-commit GitNexus re-run
```

This report combines prior GitNexus graph findings, local AST extraction, and the current MVP acceptance tests after the durable queue and sync-worker implementation.

## Code Spectrum

Current source spectrum under `src/gw2radar`:

| Metric | Count |
|---|---:|
| Python source files | 56 |
| Classes | 51 |
| Functions / methods | 148 |
| Enums | 6 |
| Pydantic models | 10 |
| SQLAlchemy models | 7 |

Domain spectrum:

| Domain | Spectrum | Maturity Signal |
|---|---|---|
| `api` | FastAPI route surface with account lifecycle | Functional MVP surface with lifecycle, goal, action, report, export routes. |
| `config` | settings model and loader | Includes database URL, GW2 API key, and local API key encryption secret config. |
| `db` | 7 SQLAlchemy models, graph repository, refresh queue repository | Mature enough for MVP persistence, deletion flows, durable queue, and encrypted key metadata. |
| `exports` | export package builder | Deterministic package generation implemented. |
| `graph` | in-memory graph and mock builder | Stable deterministic mock graph. |
| `inference` | gap, policy, action, evidence quality | Core intelligence path is implemented and tested. |
| `ingest` | gateway, client, cache, limiter, durable queue, sync services, refresh worker | Governance-first access boundary with fake-tested real sync services. |
| `ontology` | enums and Pydantic schemas | Strong semantic contract baseline. |
| `reports` | Markdown renderer | Functional, evidence-aware, still simple. |
| `security` | encrypted local key lifecycle | Fernet-encrypted SQLite key persistence with masked API responses. |

## GitNexus Flow Findings

Prior GitNexus analysis surfaced these important flows:

| Flow | Interpretation |
|---|---|
| `load_mock_data -> build_mock_graph -> add_entity/add_evidence/load_fixture` | Mock fixture graph construction is the root MVP data flow. |
| `post_generate_actions -> init_db/load_fixture/add_evidence/add_entity/quantity_owned` | Action generation crosses API, persistence, graph, and inference modules. |
| `get_markdown_report -> build_mock_graph/add_evidence/add_entity` | Report generation can hydrate graph state and render evidence-backed output. |
| `post_export_package -> load_fixture` | Export package route depends on existing graph/report/gap/action pipeline. |
| `_format_evidence_notes -> evaluate_evidence_quality` | Evidence quality is visible in report output. |

New flow anchors added in this milestone:

- `RefreshQueueRepository.enqueue/mark_retry/next_due`;
- `RefreshWorker.process_next`;
- `EncryptedApiKeyStore.set/get/delete/status`;
- `sync_account_snapshot`;
- `refresh_public_items`.

## Semantic Graph

```mermaid
flowchart TD
  Constitution["Constitution"] --> Governance["API Governance"]
  Governance --> Gateway["Gw2ApiGateway"]
  Gateway --> Cache["TTL Cache"]
  Gateway --> Limiter["Token Bucket"]
  Gateway --> Queue["Durable Refresh Queue"]
  Gateway --> Client["GW2ApiClient Skeleton"]
  Gateway --> EvidenceWriter["EvidenceWriter"]
  Queue --> RefreshWorker["RefreshWorker"]
  RefreshWorker --> Gateway

  Fixtures["Mock Fixtures"] --> GraphBuilder["build_mock_graph"]
  GraphBuilder --> GraphData["GraphData"]
  GraphData --> Repo["GraphRepository"]
  Repo --> SQLite["SQLite Models"]
  SQLite --> Repo
  Repo --> GraphData

  Ontology["Ontology Schemas + Enums"] --> GraphData
  Ontology --> Repo
  Ontology --> Inference["Inference"]

  GraphData --> GoalGap["calculate_goal_gap"]
  GoalGap --> MaterialPolicy["material_policy"]
  MaterialPolicy --> ActionGenerator["generate_actions"]
  ActionGenerator --> EvidenceQuality["apply_evidence_quality_to_action"]
  EvidenceQuality --> Actions["Recommendation Actions"]
  Actions --> Report["Markdown Report"]
  Actions --> ExportPackage["Export Package"]

  API["FastAPI Routes"] --> APIState["api.state"]
  APIState --> Repo
  API --> GoalGap
  API --> ActionGenerator
  API --> Report
  API --> ExportPackage
  API --> AccountLifecycle["API Key + Snapshot Deletion"]
  AccountLifecycle --> KeyStore["EncryptedApiKeyStore"]
  AccountLifecycle --> Repo

  Gateway --> AccountSync["Account Snapshot Sync"]
  Gateway --> PublicRefresh["Public Item Refresh"]
  AccountSync --> GraphData
  PublicRefresh --> GraphData

  Tests["Pytest + Smoke Harness"] --> API
  Tests --> Repo
  Tests --> Gateway
  Tests --> EvidenceQuality
  Tests --> ExportPackage
  Tests --> Queue
  Tests --> KeyStore
  Tests --> AccountSync
  Tests --> PublicRefresh
```

## Triple-Axis Ontology Extraction

### State Axis

| State Family | Code Anchor | Values / Meaning | Maturity |
|---|---|---|---|
| `EntityType` | `ontology/entity_types.py` | account, goal, item, recipe, task, evidence, etc. | High |
| `RelationType` | `ontology/relation_types.py` | requires, owned_by, missing_for_goal, advances_goal, etc. | High |
| `ActionType` | `ontology/action_types.py` | hold, farm, buy, do_daily, complete_achievement, etc. | High |
| `GraphLayer` | `ontology/graph_layers.py` | public_game, private_player_state, personal_intelligence | High |
| `GatewayStatus` | `ingest/gateway_status.py` | ok, cache_hit, refresh_pending, rate_limited_retrying | High |
| `RefreshQueueStatus` | `ingest/refresh_queue_status.py` | queued, delayed, processing, succeeded, failed | High |
| request priority | `ingest/request_queue.py` | P0-P4 policy string | Medium |
| action urgency | `ontology/schemas.py` | low, medium, high string | Medium |

### Entity Axis

| Semantic Entity | Code Anchor | Persistence | Maturity |
|---|---|---|---|
| Evidence | `Evidence`, `EvidenceModel`, `EvidenceWriter` | SQLite | Medium-High |
| Entity | `Entity`, `EntityModel` | SQLite | High for MVP |
| Relation | `Relation`, `RelationModel` | SQLite | High for MVP |
| PlayerState | `PlayerState`, `PlayerStateModel` | SQLite | High for MVP |
| Action | `Action`, `ActionModel` | SQLite | Medium-High |
| GraphData | `graph_query.py` | in-memory plus repository hydration | Medium-High |
| GatewayResult | `gw2_api_gateway.py` | in-memory | Medium |
| QueuedRequest | `request_queue.py`, `refresh_queue_repository.py` | SQLite durable queue | Medium-High |
| ApiKeyStatus | `security/api_key_store.py` | Fernet-encrypted SQLite storage | Medium-High for MVP |
| ExportPackage | `exports/package_builder.py` | filesystem artifacts | Medium-High |

### Constraint Axis

| Constraint | Implementation | Test Coverage | Residual Risk |
|---|---|---|---|
| No gameplay automation | Constitution, action constraints | governance/action tests | Low |
| No client/memory interaction | No modules for client control | governance scan | Low |
| No proxy/IP rotation | Gateway/client omit these features | governance/gateway tests | Low |
| API access through gateway | gateway skeleton and HTTP scan test | governance tests | Medium |
| API key masking and storage | `mask_api_key`, `EncryptedApiKeyStore`, key lifecycle tests | client/security tests | Medium until KMS or OS vault integration exists |
| Private/public graph separation | `GraphLayer`, repository validation | graph layer tests | Medium |
| Evidence freshness/confidence | `evidence_quality.py` | evidence tests | Medium |
| 429 handling | gateway status and durable retry metadata | gateway/queue tests | Medium |
| Deterministic export package | package builder + manifest | export/smoke tests | Low-Medium |
| Account snapshot deletion | repository deletion + API route | lifecycle tests | Medium |
| Account snapshot sync | gateway-bounded sync service | fake gateway tests | Medium |
| Public item refresh | gateway batch service | fake gateway tests | Medium |

## MVP Functional Maturity

Scoring: 0 = absent, 5 = production-grade.

| Capability | Score | Current State |
|---|---:|---|
| Constitution / governance baseline | 4.2 | Strong docs, tests, safety constraints, key/snapshot lifecycle. |
| Ontology and semantic schema | 4.2 | Core enums, graph layers, Pydantic schemas, persistence mapping. |
| Mock legendary-goal graph | 4.3 | Deterministic Aurora loop with evidence and layers. |
| Goal gap inference | 4.1 | Simple deterministic rule, tested. |
| Material policy | 3.7 | HOLD/RESERVE conservative policy; SELL_SURPLUS mostly gated. |
| Action generation | 3.8 | Explanations, reason codes, evidence refs, quality downgrades. |
| Evidence governance | 3.7 | Masking, freshness/confidence, report labels, action effects. |
| Graph layer separation | 3.7 | Schema + DB fields + repository validation. |
| SQLite persistence | 3.8 | Replace/load/delete flows, queue, key metadata, migrations. Repository still coarse-grained. |
| FastAPI MVP surface | 3.5 | Health, mock load, goals, gap, actions, reports, export, lifecycle. |
| Export package | 3.8 | Markdown/CSV/manifest package, deterministic and tested. |
| GW2 API gateway/client | 3.6 | Safe fake-tested skeleton with sync services and worker contracts behind the gateway. |
| Refresh queue durability | 3.4 | SQLite queue, retry metadata, status transitions, and one-step worker contract. |
| Production key storage | 3.0 | Local Fernet-encrypted SQLite storage; KMS or OS vault remains future production hardening. |
| Real account ingestion | 3.0 | Account snapshot sync service writes private player state using gateway fake transport tests. |
| Public static data refresh | 3.2 | Public item batch refresh writes public-game entities through gateway contract. |

Overall MVP maturity: **3.85 / 5.0**.

Interpretation: GW2Radar is now a governed, test-backed MVP substrate with durable refresh state, encrypted local key storage, and gateway-bounded sync services. It is still not a production account-ingestion service until scheduling, monitoring, and external secret management are added.

## Feature Completion Matrix

| Feature | Status |
|---|---|
| Mock account data | Complete |
| Mock Aurora goal | Complete |
| Requirement graph | Complete |
| Player owned graph | Complete |
| Goal gap inference | Complete |
| HOLD / RESERVE / DO_DAILY / COMPLETE_ACHIEVEMENT actions | Complete |
| Markdown report | Complete |
| Markdown/CSV/manifest export package | Complete |
| SQLite graph persistence | Complete for MVP |
| Graph layer separation | Complete for MVP |
| API governance skeleton | Complete for MVP |
| Safe API client skeleton | Complete for MVP |
| Evidence quality downgrades | Complete for MVP |
| API key delete | Complete for MVP encrypted local store |
| Account snapshot delete | Complete for MVP |
| Durable refresh queue | Complete for MVP |
| Production encrypted key storage | Complete for local MVP; external vault deferred |
| Real GW2 account sync | Complete for MVP service layer with fake transport tests |
| Real public data refresh worker | Complete for MVP service layer with fake transport tests |

## Recommended Next Priority

### P0: Release Readiness Hardening

Reason: the previously immature infrastructure paths are now implemented for MVP. The next highest-value work is making the API and operations surface release-ready without expanding product scope.

Minimum deliverables:

- uniform API error envelope;
- route-level OpenAPI response schemas;
- repository update operations for partial sync instead of full graph replacement only;
- fake-gateway smoke command covering refresh queue, account sync, and public item refresh together;
- GitNexus re-analysis after commit.

## Constitution Compliance Summary

- Gameplay automation: absent.
- Game client interaction: absent.
- Memory reading/modification: absent.
- Automated trading: absent.
- Proxy/IP rotation: absent.
- API key logging: not present in implemented client/tests.
- Raw evidence key storage: sanitized or encrypted.
- Public/private layer leakage: guarded by repository validation.
- Recommendation-only boundary: present in actions, reports, and export manifest.

## Notes on GitNexus Coverage

GitNexus should be re-run after this implementation is committed because it indexes by commit. The post-commit graph should include the new durable queue, refresh worker, encrypted key store, account snapshot sync, and public item refresh anchors.
