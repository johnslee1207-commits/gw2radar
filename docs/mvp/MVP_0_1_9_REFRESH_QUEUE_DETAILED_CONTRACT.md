# MVP 0.1.9 Refresh Queue Detailed Contract

Date: 2026-06-16

## Source Spec

`GW2Radar_Post_MVP_Development_Tasks_Detailed_Design_Codex_Spec.md` identified the next post-MVP task as P0 Durable Refresh Queue.

The repository already had a lightweight durable queue from MVP 0.1.8. This slice upgrades it to the detailed post-MVP contract while keeping the existing gateway and worker paths compatible.

## Priority Assessment

Current task priority after review:

| Priority | Status | Decision |
|---|---|---|
| P0 Durable Refresh Queue | Completed in detailed-contract form | Implemented now. |
| P1 Official GW2 API Compatibility Hardening | Next | Required before broad real account sync. |
| P2 Account Snapshot Sync Pipeline | Partially complete at service layer | Needs P1 tokeninfo and permission validation before route productization. |
| P3 Public Static Data Refresh Worker | Partially complete at service layer | Needs enqueue/planner/evidence expansion after P1. |
| P4 Returner Account Diagnosis | Pending | Depends on stable synced account state. |
| P5 Production Security Upgrade | Partially complete for local mode | External KMS/OS vault remains future hardening. |

## Implemented Contract

- `RefreshQueueStatus`: queued, delayed, processing, succeeded, failed.
- `RefreshQueuePriority`: P0 active goal through P4 market history backfill.
- `RefreshTaskType`: account snapshot sync, public static refresh, goal price refresh, market history backfill.
- `RefreshQueueCreate` and `RefreshQueueItem` Pydantic schemas.
- Expanded `refresh_queue` SQLAlchemy model and Alembic migration `0005`.
- Repository methods:
  - `enqueue`;
  - `list_by_status`;
  - `lease_next`;
  - `mark_done`;
  - `mark_retry`;
  - `mark_failed`;
  - `delete_completed_older_than`.

## Safety And Sanitization

Queue params are sanitized before persistence. The queue does not store:

- API keys;
- Authorization headers;
- access tokens;
- proxy URLs;
- outbound IP fields;
- IP rotation metadata;
- raw private account payloads.

Allowed persisted metadata remains limited to endpoint, method, sanitized params, params hash, account id, feature scope, retry timestamps, status code, and error code/message.

## Verification

Added coverage:

- `tests/test_refresh_queue_model.py`;
- `tests/test_refresh_queue_repository.py`;
- `tests/test_refresh_queue_retry_persistence.py`;
- `tests/test_refresh_queue_429_persistence.py`;
- `tests/test_refresh_queue_no_secret_leakage.py`.

Full verification:

```text
python -m pytest
python harness/run_smoke.py
python -m alembic upgrade head
```

## Next Milestone

P1 Official GW2 API Compatibility Hardening:

- tokeninfo client method;
- permission validator;
- official endpoint schema;
- structured client errors;
- stronger tests for Authorization-only private access;
- failed official responses must not write graph facts.
