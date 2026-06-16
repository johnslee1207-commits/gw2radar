# MVP 0.2.1 Account Sync API Productization

Date: 2026-06-16

## Scope

This milestone implements P2 from the post-MVP roadmap: queue-backed account snapshot sync API routes, developer drain-one execution, status reporting, and private-layer verification.

## Implemented API

```http
POST /api/v1/account/sync
GET  /api/v1/account/sync/status
POST /api/v1/account/sync/drain-one
```

`drain-one` is an MVP developer utility. It processes at most one queued account snapshot task and remains deterministic for tests.

## Sync Flow

```text
encrypted local API key
-> tokeninfo permission validation
-> durable account_snapshot_sync task
-> drain-one lease
-> Gw2ApiGateway fake/official-compatible calls
-> sync_account_snapshot
-> private player state graph
-> GraphRepository persistence
-> queue mark_done / mark_retry
```

## Private Endpoints

The account sync contract covers:

- `/v2/account`;
- `/v2/characters`;
- `/v2/account/wallet`;
- `/v2/account/materials`;
- `/v2/account/bank`;
- `/v2/account/achievements`.

## Safety Boundary

- API keys are read from encrypted local storage and never returned by sync responses.
- Queue payload stores only sanitized sync metadata.
- Account entity and character entities are private.
- Player state and account ownership relations are private.
- Failed or pending gateway responses do not create graph facts.
- No gameplay automation, client interaction, proxy pool, IP rotation, or trading automation is implemented.

## Verification

Added:

- `tests/test_account_sync_api.py`.

Updated:

- `tests/test_sync_workers.py`.

Full verification:

```text
python -m pytest
python harness/run_smoke.py
python -m alembic upgrade head
```

## Next Milestone

P3 Public Static Refresh Planner:

- enqueue public static refresh tasks;
- dedupe/sort/chunk ids;
- batch official endpoint calls;
- evidence metadata per official response;
- public-game-only writes;
- cache tests proving no N+1 path.
