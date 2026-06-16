# MVP 0.1.4 Gateway Contract Hardening

MVP 0.1.4 tightens the GW2 API access boundary without enabling real network access by default.

## Implemented Contracts

- `GatewayStatus` enum replaces free-form status strings.
- `endpoint_ttl_seconds()` centralizes endpoint TTL resolution.
- `Gw2ApiGateway.get_batch()` builds a single batch request for supported endpoints.
- `QueuedRequest` records retry metadata:
  - `attempts`
  - `retry_after_seconds`
  - `next_attempt_at`
  - `last_error`

## Batch Endpoints

The MVP batch helper only supports endpoints listed by API governance:

- `/v2/items`
- `/v2/recipes`
- `/v2/achievements`
- `/v2/commerce/prices`
- `/v2/commerce/listings`
- `/v2/skins`
- `/v2/traits`
- `/v2/skills`

Unsupported endpoints and empty batches raise `ValueError`.

## Safety Boundary

This milestone does not implement:

- real GW2 HTTP access;
- proxy pools;
- IP rotation;
- rate-limit evasion;
- automated trading;
- gameplay automation.

## Verification

Covered by:

- `tests/test_gateway_contract.py`
- `tests/test_api_governance.py`
- `python harness/run_smoke.py`
