# Software Design Document

## 1. System Overview

GW2Radar is a local-first Guild Wars 2 intelligence system. It combines public
game data, private player account summaries, personal intelligence, reviewed KB
evidence, deterministic planners, productized reports, and delivery lifecycle
artifacts.

The system is designed for manual player and operator review. It must not
automate gameplay, automate trading, publish external content, leak secrets, or
claim guaranteed outcomes.

## 2. Core Data Layers

```text
official/public GW2 data -> public_game graph layer
private GW2 account API summaries -> private_player_state graph layer
derived recommendations/history/readiness -> personal_intelligence graph layer
reviewed docs/rules/patch evidence -> knowledge_base layer
reports/support packets -> deterministic delivery artifacts
```

Layer separation is a hard safety boundary. Public KB content must not contain
raw private account data. Delivery artifacts must not contain raw API keys, raw
debug bundles, private source payloads, or executable content.

## 3. Main Modules

### API And State

FastAPI routes expose account lifecycle, player cockpit, reports, KB, acquisition
queues, market/account refresh, achievement routes, and support workflows. Shared
state loads deterministic mock graph data for local smoke testing.

### Persistence

SQLite stores graph entities, refresh queues, account sync status, encrypted
secrets, report jobs, histories, KB/rule metadata, audit trails, and local
operator artifacts.

### Gateway And Refresh Workers

GW2 API access is mediated by `Gw2ApiGateway` contracts. Queue-backed workers
handle account sync, public refresh, and market price refresh with retry metadata,
worker health, and user-facing diagnostics.

### Commercial Intelligence

Commercial modules produce account value snapshots, Legendary Planner Pro,
Build Fit, Market Radar, guild/static readiness, creator intelligence, growth
pages, productized reports, and entitlement-gated report artifacts.

### Knowledge Base

KB modules manage source registry, PDF/source processing, semantic maturity,
entity/action linking, reviewed rule packs, patch review, release readiness,
and KB-backed report explanations.

### Delivery Lifecycle

`gw2radar.delivery.lifecycle` centralizes deterministic zip construction,
whitelist verification, checksum calculation, no-secret marker checks, readiness
gating, and metadata-only audit evidence. Domain modules keep their domain
schemas and payload validation while reusing the shared lifecycle primitives.

### UI And Harness

The Player UI serves the local player cockpit. Harness commands verify the mock
legendary loop, player UI, account connection diagnostic, achievement route
workflow, and staged validation gates.

## 4. Primary Pipelines

### Account-Aware Recommendation Pipeline

```text
API key status -> permission inspection -> sync queue -> private state write ->
account value evidence -> readiness / planner / build fit / market reports
```

### KB Review Pipeline

```text
source registry -> seed/import -> link entities/actions -> review candidate ->
persist disabled rule -> explicit enable gate -> audit/export/readiness
```

### Productized Report Pipeline

```text
entitlement -> deterministic report template -> artifact manifest ->
delivery zip -> verification -> metadata audit -> checklist/operator handoff
```

### Support Handoff Pipeline

```text
readiness/session packet -> support handoff artifacts -> zip verification ->
metadata audit -> operator packet -> final archive / closure packet
```

## 5. API Design Principles

- Use `ApiDataEnvelope` for versioned JSON responses.
- Preserve path-safe artifact retrieval.
- Return structured diagnostics rather than silent empty states.
- Keep upload/zip verification read-only and metadata-only.
- Use explicit reviewer confirmation for promotion, enable, apply, and sign-off
  gates.

## 6. State And Safety Model

Important lifecycle states include missing key, permission-limited, queued,
processing, retryable, failed, ready, needs review, reviewed, persisted,
enabled, archived, signed off, and blocked.

Safety constraints:

- Never store raw API keys in source code or responses.
- Never expose raw private account payloads in public KB or report artifacts.
- Never execute uploaded files or zip contents.
- Never generate guaranteed-return or automated-trading claims.
- Every delivery packet needs checksum and whitelist validation.

## 7. Validation Strategy

Default stage gate:

```bash
python harness/run_stage_gate.py stage
```

Release/milestone gate:

```bash
python harness/run_stage_gate.py release
```

The `stage` gate runs fast and smoke profiles. The `release` gate adds full
pytest. The player use-path maturity audit records executable checklist status
and semantic graph maturity.
