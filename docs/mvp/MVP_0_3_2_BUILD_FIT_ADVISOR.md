# MVP 0.3.2 Build Fit & Gear Transition Advisor

Date: 2026-06-16

## Scope

This milestone implements P8 Build Fit & Gear Transition Advisor on top of the P6 Paid Report Engine and P7 commercial planning foundation.

## Implemented

- `Build` persistence model.
- Structured manual build import.
- `BuildRequirement` / `GearRequirement` schema.
- `AccountGearSnapshot` schema.
- Account gear matcher.
- Weighted build fit score:

```text
0.30 gear_match
+ 0.20 unlock_match
+ 0.15 cost_affordability
+ 0.15 difficulty_match
+ 0.10 preferred_mode_match
+ 0.10 patch_freshness
```

- Gear transition plan.
- Budget alternative recommendation.
- Build Fit Markdown report.
- P6-backed paid report job generation.
- Versioned Build Fit API routes:

```http
POST /api/v1/builds/import
GET  /api/v1/builds
POST /api/v1/builds/fit
POST /api/v1/builds/transition-plan
POST /api/v1/builds/report
```

## Commercial Boundaries

- Build import is structured/manual in the MVP.
- No aggressive third-party scraping is implemented.
- Source attribution is preserved.
- Build freshness warnings are explicit.
- No gameplay automation is created.
- No automatic gear changes are performed.
- Recommendations are informational only.

## Verification

Added tests:

- `tests/test_build_requirement_schema.py`;
- `tests/test_account_gear_matcher.py`;
- `tests/test_build_fit_score.py`;
- `tests/test_gear_transition_cost.py`;
- `tests/test_budget_alternative.py`;
- `tests/test_build_report.py`;
- `tests/test_build_source_attribution.py`;
- `tests/test_no_automatic_gear_change.py`;
- `tests/test_build_fit_api.py`.

Required verification:

```text
python -m pytest
python harness/run_smoke.py
python harness/run_sync_smoke.py
python -m alembic upgrade head
```

## Next Milestone

P9 Market Radar Pro:

- price snapshots;
- price trend calculator;
- goal cost index;
- material watchlist;
- hold/sell candidate inference;
- market language policy;
- Market Radar paid report.
