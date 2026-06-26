# Trust Semantics

## Confidence Thresholds

| Range | Label | Meaning |
|-------|-------|---------|
| `0.90+` | High trust | Data is fresh, prices exist, no known risk factors. Safe to act on with standard caution. |
| `0.70–0.89` | Moderate trust | Actionable but needs review. Price may be stale, holding may be reserved, or signal may have medium liquidity. |
| `< 0.70` | Low trust | Insufficient or unreliable data. Missing price, account-bound, unclear intent, or very low liquidity. Verify manually before acting. |

## Data Source Semantics

| Source | Meaning |
|--------|---------|
| `official_items` / `official_itemstats` | GW2 API item/stat data. High baseline trust. |
| `manual_snapshot` | Player-recorded price snapshot. Trust depends on recency. |
| `official_price_refresh` | Bulk official TP price refresh. Trust depends on staleness check. |
| `player_cockpit` | Derived from player dashboard aggregation. Moderate trust, depends on upstream sync. |

## Field Reference

| Field | Appears On | Meaning |
|-------|-----------|---------|
| `confidence` | AccountValueHolding, MarketSignal, PlanAction | 0–1 score based on data quality, price freshness, tradability, and reservation status. |
| `liquidity_score` | AccountValueHolding, MarketSignal | 0–1 based on trading volume (market snapshots). 0 = illiquid, 1 = highly liquid. |
| `risk_reason` | AccountValueHolding, MarketSignal, PlanAction | Human-readable explanation of the primary risk factor, if any. |
| `liquidity_note` | PlanAction | Contextual note about market liquidity for sell/buy actions. |

## Risk Reason Mapping

| Warning Code | Risk Reason |
|-------------|-------------|
| `missing_price` | No market price data available. |
| `stale_price` | Price > 48h old. |
| `account_bound` | Cannot be sold on TP. |
| `reserved_for_goal` | Partly reserved; surplus may be available. |
| Low liquidity (< 0.3) + SELL signal | Low liquidity; selling may take time at a fair price. |
| BUY_WAIT signal | Price above recent average; waiting may reduce cost. |
| HOLD signal | Required by active goal; verify reservations before selling. |
