# MVP 0.1.8 Durable Queue And Sync Workers

Date: 2026-06-16

## Scope

This slice closes the remaining immature MVP infrastructure items identified by the GitNexus maturity report:

- SQLite-backed refresh queue;
- encrypted local API key persistence;
- account snapshot sync service behind `Gw2ApiGateway`;
- public item refresh service behind `Gw2ApiGateway`;
- single-step refresh worker with persisted retry state.

## Durable Refresh Queue

`RefreshQueueRepository` persists refresh requests in `refresh_queue` with request id, endpoint, params, priority, status, retry attempts, retry-after seconds, next attempt time, and last error.

The MVP state model is:

```text
queued -> processing -> succeeded
queued -> processing -> delayed -> processing
queued -> processing -> failed
```

`DurableRequestQueue` keeps the existing lightweight queue interface while writing enqueue events to SQLite.

## API Key Storage

`EncryptedApiKeyStore` stores one local API key record in `api_key_secrets` using Fernet encryption derived from `GW2RADAR_API_KEY_ENCRYPTION_SECRET`.

The API surface still returns only configured flag, masked key, and storage kind. It never returns the raw API key.

## Account Snapshot Sync

`sync_account_snapshot` uses only `Gw2ApiGateway` calls:

- `/v2/account`;
- `/v2/account/wallet`;
- `/v2/account/materials`;
- `/v2/account/achievements`.

The service writes account facts into `private_player_state` and preserves public catalog entities in `public_game`.

## Public Static Refresh

`refresh_public_items` uses gateway batch access and writes item entities only to `public_game`.

## Safety Boundary

This milestone does not add gameplay automation, client interaction, proxy behavior, automated trading, or direct background scheduling. The refresh worker processes one due request per call so it remains deterministic and testable.

## Verification

Covered by:

- `tests/test_durable_refresh_queue.py`;
- `tests/test_encrypted_api_key_store.py`;
- `tests/test_sync_workers.py`;
- existing account lifecycle and graph layer tests.
