# MVP 0.2.0 Official API Compatibility Hardening

Date: 2026-06-16

## Scope

This milestone implements P1 from the post-MVP roadmap. It hardens the official Guild Wars 2 API compatibility layer before productizing real account sync routes.

## Implemented

- Official endpoint schema for private and public batch endpoints.
- `Gw2EndpointKind` and `Gw2EndpointSchema`.
- `TokenInfo` parser and permission validator.
- `GW2ApiClient.fetch_tokeninfo`.
- Gateway private-endpoint preflight:
  - missing API key returns `permission_denied`;
  - missing token permission returns `permission_denied`;
  - tokeninfo 429 returns `rate_limited_retrying`;
  - official client failure returns structured `error` diagnostics.
- Batch endpoint set now derives from endpoint schema.
- Evidence sanitization tests cover Authorization/API key/token payloads.

## Permission Mapping

| Endpoint | Required Permission |
|---|---|
| `/v2/account` | `account` |
| `/v2/characters` | `characters` |
| `/v2/account/wallet` | `wallet` |
| `/v2/account/materials` | `inventories` |
| `/v2/account/bank` | `inventories` |
| `/v2/account/achievements` | `progression` |

## Safety Boundary

This milestone does not add gameplay automation, trading automation, proxy pools, IP rotation, or rate-limit evasion.

API keys remain Authorization-header only and are excluded from URLs, queue payloads, evidence, reports, and structured diagnostics.

## Verification

Added tests:

- `tests/test_gw2_api_client_official_contract.py`;
- `tests/test_gw2_api_permissions.py`;
- `tests/test_gw2_api_batching.py`;
- `tests/test_gw2_api_rate_limit_behavior.py`;
- `tests/test_gw2_api_key_safety.py`;
- `tests/test_gw2_api_evidence_sanitization.py`.

Full verification:

```text
python -m pytest
python harness/run_smoke.py
python -m alembic upgrade head
```

## Next Milestone

P2 Account Sync API Productization:

- `POST /api/v1/account/sync`;
- `GET /api/v1/account/sync/status`;
- developer `POST /api/v1/account/sync/drain-one`;
- queue-backed sync orchestration;
- tokeninfo validation before private sync;
- private-layer-only writes.
