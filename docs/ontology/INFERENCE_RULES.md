# Inference Rules

Goal gap:

```text
if owned_quantity >= required_quantity:
    missing_quantity = 0
else:
    missing_quantity = required_quantity - owned_quantity
```

Material policy:

- Required materials with owned quantities produce RESERVE_FOR_GOAL or HOLD actions.
- Missing materials produce BUY, FARM, WATCH_PRICE, or task actions when supported by mock data.
- Legendary-related materials are not recommended for SELL_SURPLUS in MVP 0.1.

Ranking:

- Base score is 0.5.
- Advancing the active goal adds 0.2.
- Resolving a missing requirement adds 0.2.
- Daily or time-gated work adds 0.1.
- Low estimated time adds 0.05.
- Protecting required material adds 0.1.
- Score is capped at 1.0.
