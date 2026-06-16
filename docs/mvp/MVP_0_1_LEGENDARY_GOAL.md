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
- `/mock/load` loads mock entities, relations, evidence, and player state.
- `/goals` returns Aurora.
- `/goals/{goal_id}/gap` reports completed and missing requirements.
- `/goals/{goal_id}/actions/generate` returns explainable actions.
- `/reports/{goal_id}/markdown` returns the required report sections.
