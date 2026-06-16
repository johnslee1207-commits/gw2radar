# MVP 0.2.2 Public Static Refresh Planner

Date: 2026-06-16

## Scope

This milestone implements P3 from the post-MVP roadmap: queue-backed public static refresh planning, stable batching, evidence metadata, public-game-only writes, and cache/no-N+1 tests.

## Implemented API

```http
POST /api/v1/public/refresh
GET  /api/v1/public/refresh/status
POST /api/v1/public/refresh/drain-one
```

`drain-one` is an MVP developer utility. It processes at most one queued public static refresh task and remains deterministic for tests.

## Supported Endpoints

- `/v2/items`
- `/v2/achievements`
- `/v2/currencies`
- `/v2/recipes`

## Planner Rules

- Deduplicate ids.
- Sort ids for stable request planning.
- Chunk ids by request chunk size.
- Use `Gw2ApiGateway.get_batch`.
- Persist only public-game entities.
- Store evidence metadata per official response.
- Reuse gateway cache to avoid duplicate client calls.

## Safety Boundary

- No API key is required.
- No private player state writes.
- No gameplay automation.
- No trading automation.
- No proxy pool or IP rotation.
- Unsupported private endpoints are rejected before enqueue.

## Verification

Added:

- `tests/test_public_static_refresh_api.py`;
- `tests/test_public_static_refresh_planner.py`.

Updated:

- `tests/test_sync_workers.py`.

Full verification:

```text
python -m pytest
python harness/run_smoke.py
python -m alembic upgrade head
```

## Next Milestone

P4 Release Readiness Hardening:

- uniform API error envelope;
- route-level response schemas;
- sync smoke harness using fake gateway;
- operational status summary endpoint.
