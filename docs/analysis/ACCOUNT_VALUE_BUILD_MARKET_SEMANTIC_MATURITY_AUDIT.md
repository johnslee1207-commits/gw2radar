# Account Value, Build Fit, And Market Semantic Maturity Audit

Date: 2026-06-20

## Scope

This audit covers the account-value development line that started from the
`gw2-progression` reference review and now spans API key value readiness,
private holding summaries, conservative account value snapshots, player
dashboard visualization, Legendary/Market reservation safety, Build Fit gear
transition context, and paid report artifact manifests.

## Implemented Semantic Graph

```mermaid
flowchart TD
  ApiKey["API Key Permission Report"] --> Readiness["Value Analysis Readiness"]
  Readiness --> Modules["Unlocked / Blocked Analysis Modules"]
  Sync["Private Account Sync"] --> PlayerState["Private Player State"]
  PlayerState --> HoldingIndex["Account Holding Index"]
  Prices["Market Price Snapshots"] --> ValueSnapshot["Account Value Snapshot"]
  HoldingIndex --> ValueSnapshot
  Goals["Active Legendary Goals"] --> Reservation["Goal Reservation Overlay"]
  Reservation --> ValueSnapshot
  ValueSnapshot --> Dashboard["Player Value Dashboard"]
  ValueSnapshot --> Market["Market Radar Signals"]
  ValueSnapshot --> BuildFit["Build Fit Transition Context"]
  ValueSnapshot --> Reports["Paid Report Artifact Manifest"]
  Reservation --> Market
  Reservation --> BuildFit
```

## Mature Capabilities

| Capability | Status | Evidence |
|---|---|---|
| API key value readiness | Implemented | `ApiKeyPermissionReport.value_analysis_readiness`, unlocked/blocked modules |
| Private holding index | Implemented | `AccountHoldingIndex`, `/api/v1/player/account-holdings` |
| Conservative value snapshot | Implemented | `/api/v1/player/account-value`, Markdown/CSV exports |
| Dashboard visualization | Implemented | Account value summary, location/status breakdown, top holdings, warnings |
| Goal reservation overlay | Implemented | `reserved_quantity`, `sellable_surplus_quantity`, `reserved_for_goal_ids` |
| Market sell safety | Implemented | Reserved active-goal materials are not emitted as sell surplus |
| Build Fit value context | Implemented | transition plan value context, reserved/unpriced/account-bound notes |
| Paid report artifact manifest | Implemented | `account_value_snapshot` metadata in report manifest |

## Safety Boundaries

- Raw API keys are not returned by permission, holding, value, dashboard,
  market, build, or report APIs.
- Account value snapshots are private summaries, not raw private payload dumps.
- Value calculations are planning estimates only.
- Market output never places orders, automates trades, or guarantees returns.
- Active goal requirements are reserved before any surplus/sell candidate
  interpretation.
- Build Fit never changes gear and treats value context as manual planning
  evidence only.

## Test Coverage

Latest targeted verification covered:

- `tests/test_account_value_holding_index.py`
- `tests/test_do_not_sell_multi_goal.py`
- `tests/test_sell_candidate.py`
- `tests/test_hold_candidate.py`
- `tests/test_no_auto_trading.py`
- `tests/test_market_api.py`
- `tests/test_gear_transition_cost.py`
- `tests/test_build_fit_api.py`
- `tests/test_report_no_secret_leakage.py`
- `tests/test_paid_report_api_routes.py`
- `tests/test_player_ui.py`
- `tests/test_player_dashboard_completion.py`
- `harness/run_account_connection_diagnostic.py`
- `harness/run_player_ui_e2e_smoke.py`
- `harness/run_smoke.py`

## Remaining Gaps

1. Shared inventory and trading-post order holdings are represented in the
   semantic model but still depend on sync-layer endpoint expansion.
2. Price snapshots remain manual/stored observations. Official commerce refresh
   orchestration should be added before relying on live-ish value coverage.
3. Value dashboard is text/list based. Richer charts can be added later, but the
   current MVP intentionally favors deterministic, testable output.
4. Build Fit value context is account-level. Slot-to-item price mapping should
   be refined when build requirements include official item ids.
5. Report manifests include summary metadata. Full per-holding report exports
   should remain opt-in and privacy-gated.

## Next Priority

Proceed to official commerce price refresh orchestration for value snapshots:

1. derive item ids from `AccountHoldingIndex`;
2. batch `/v2/commerce/prices` through the existing gateway/cache/rate-limit
   layer;
3. write `MarketSnapshotModel` observations with source `official_commerce_api`;
4. surface stale/missing price remediation in the Player Dashboard;
5. preserve the manual-planning and no-auto-trading boundary.

