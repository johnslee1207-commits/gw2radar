# MVP 0.1 Legendary Goal Intelligence

MVP 0.1 validates one loop:

```text
player goal -> requirements -> owned resources -> gap -> actions -> Markdown report
```

Implemented mock target:

- Account: `mock:account:lee`
- Goal: `gw2:goal:aurora`
- Daily task: `gw2:task:bitterfrost_daily`

Acceptance checks:

- `/health` returns `{"status": "ok"}`.
- `/mock/load` idempotently loads mock entities, relations, evidence, and player state into SQLite.
- `/goals` returns Aurora.
- `/goals/{goal_id}/gap` reports completed and missing requirements.
- `/goals/{goal_id}/actions/generate` returns explainable actions.
- `/reports/{goal_id}/markdown` returns the required report sections.

MVP 0.1.1 hardening:

- API state can be rebuilt from SQLite after the in-process cache is reset.
- Generated actions are persisted after `/goals/{goal_id}/actions/generate`.
- Smoke harness uses FastAPI TestClient plus a temporary SQLite database.
