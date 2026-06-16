# MVP 0.1.7 API Key and Account Snapshot Lifecycle

MVP 0.1.7 implements the Constitution requirement to support API key deletion and account snapshot deletion.

## API Key Lifecycle

Endpoints:

```http
GET /account/api-key/status
PUT /account/api-key
DELETE /account/api-key
```

MVP behavior:

- API keys are stored in process memory only.
- API keys are never written to SQLite.
- API responses return only masked keys.
- Deletion clears the in-memory key.

This is not production encrypted storage. Production storage remains a future milestone.

## Account Snapshot Deletion

Endpoint:

```http
DELETE /account/snapshot
```

Deletes persisted private and derived data:

- private account entity;
- player state rows;
- `OWNED_BY` relations;
- personal intelligence relations;
- generated actions.

Keeps public game graph data:

- Aurora goal;
- item/currency/achievement/task entities;
- public `REQUIRES` and `PRODUCES` relations.

## Safety Boundary

This milestone does not implement login, user accounts, real key persistence, production encryption, game automation, trading automation, proxy pools, or IP rotation.
