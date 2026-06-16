# MVP 0.3.3 Market Radar Pro

Date: 2026-06-16

## Scope

This milestone implements P9 Market Radar Pro on top of P6 Paid Report Engine, P7 Legendary Planner Pro, and P8 Build Fit Advisor.

## Implemented

- `MarketSnapshot` persistence model.
- `MarketWatchlist` persistence model.
- Price snapshot ingestion.
- Price trend calculator.
- Goal cost index.
- Material watchlist.
- Hold candidate inference.
- Sell-surplus candidate inference.
- Buy-wait observation suggestion.
- Market language policy.
- Market Radar Markdown report.
- P6-backed paid report job generation.
- Versioned Market Radar API routes:

```http
GET  /api/v1/market/watchlist
POST /api/v1/market/watchlist
POST /api/v1/market/snapshots
GET  /api/v1/market/goal-cost-index
GET  /api/v1/market/signals
POST /api/v1/market/report
```

## Commercial Boundaries

- No automated trading.
- No order placement.
- No real-money exchange support.
- No guaranteed-profit language.
- No high-frequency arbitrage.
- Suggestions use observation, hold, and consider-selling-surplus language.
- All outputs are planning guidance only.

## Verification

Added tests:

- `tests/test_price_snapshot.py`;
- `tests/test_price_trend.py`;
- `tests/test_goal_cost_index.py`;
- `tests/test_hold_candidate.py`;
- `tests/test_sell_candidate.py`;
- `tests/test_market_language_policy.py`;
- `tests/test_no_auto_trading.py`;
- `tests/test_market_api.py`.

Required verification:

```text
python -m pytest
python harness/run_smoke.py
python harness/run_sync_smoke.py
python -m alembic upgrade head
```

## Next Milestone

P12 Growth Website + CMS + Payment Abstraction:

- landing page models;
- CMS content model;
- pricing model;
- payment provider interface;
- mock checkout session;
- entitlement integration;
- mandatory privacy and API key safety pages.
