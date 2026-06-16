# MVP 0.2.3 Release Readiness Hardening

Date: 2026-06-16

## Scope

This milestone implements P4A release-readiness hardening after account sync and public static refresh were productized.

## Implemented

- Uniform HTTP error envelope for `HTTPException` responses.
- `ApiError`, `ApiErrorEnvelope`, and `ApiDataEnvelope` schemas.
- Operational status endpoint:

```http
GET /api/v1/ops/status
```

- Fake-gateway sync smoke harness:

```text
python harness/run_sync_smoke.py
```

## Error Envelope

HTTP errors now return:

```json
{
  "ok": false,
  "error": {
    "code": "not_found",
    "message": "Goal not found",
    "details": {
      "path": "/goals/not-a-goal/gap"
    }
  }
}
```

## Operational Status

The operational status endpoint reports:

- database status;
- graph object counts;
- refresh queue counts;
- API key configured flag;
- enabled capabilities.

## Smoke Coverage

`harness/run_sync_smoke.py` verifies:

- encrypted API key lifecycle does not leak raw key;
- account sync enqueue and drain-one work with fake gateway;
- public refresh enqueue and drain-one work with fake gateway;
- operational status endpoint returns an envelope response.

## Verification

```text
python -m pytest
python harness/run_smoke.py
python harness/run_sync_smoke.py
python -m alembic upgrade head
```

## Next Milestone

Recommended next milestone depends on deployment target:

- For local/private intelligence value: P4B Returner Account Diagnosis.
- For real users or hosted deployment: P5 Production Security Upgrade.
