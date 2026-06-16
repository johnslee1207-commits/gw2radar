# MVP 0.3.1 Legendary Planner Pro

Date: 2026-06-16

## Scope

This milestone implements P7 Legendary Planner Pro on top of the P6 Paid Report Engine.

## Implemented

- `GoalPortfolio` model.
- `LegendaryGoal` persistence model.
- Shared requirement inference.
- Goal conflict inference.
- Time-gated requirement detection.
- Acquisition method inference from task evidence.
- Cheap path and fast path planning.
- Multi-goal do-not-sell material reservation.
- Daily and weekly legendary routes.
- Legendary Planner Pro Markdown report.
- P6-backed paid report job generation.
- Versioned Legendary Planner Pro API routes:

```http
POST /api/v1/legendary/goals
GET  /api/v1/legendary/portfolio
POST /api/v1/legendary/recompute
GET  /api/v1/legendary/do-not-sell
POST /api/v1/legendary/report
```

## Commercial Boundaries

- Recommendations are informational only.
- No gameplay automation is created.
- No automated trading is created.
- Cheap and fast paths are planning suggestions, not farming automation.
- Paid report generation requires a P6 entitlement.
- Report artifacts do not expose API keys or unredacted private payloads.

## Verification

Added tests:

- `tests/test_goal_portfolio.py`;
- `tests/test_shared_requirements.py`;
- `tests/test_goal_conflicts.py`;
- `tests/test_time_gate_inference.py`;
- `tests/test_do_not_sell_multi_goal.py`;
- `tests/test_cheap_path.py`;
- `tests/test_fast_path.py`;
- `tests/test_legendary_pro_report.py`;
- `tests/test_legendary_pro_api.py`.

Required verification:

```text
python -m pytest
python harness/run_smoke.py
python harness/run_sync_smoke.py
python -m alembic upgrade head
```

## Next Milestone

P8 Build Fit & Gear Transition Advisor:

- build import schema;
- gear requirement model;
- account gear matcher;
- build fit score;
- gear transition plan;
- budget alternative recommendation;
- Build Fit paid report.
