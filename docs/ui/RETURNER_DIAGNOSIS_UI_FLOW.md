# Returner Diagnosis UI Flow

## User Intent

A returning player wants to know what to do first without relearning every system at once.

## Flow

1. Confirm account sync in `Dashboard`.
2. Open `Returner`.
3. Select last-played range and main interest.
4. Load current goals.
5. Run readiness score.
6. Inspect Aurora gap.
7. Generate a 7-day action plan.
8. Open KB-backed report preview when evidence context is needed.
9. Generate the entitlement-gated full returner report when the player wants the durable artifact.

## Output Expectations

- Completed and missing requirements are separated.
- Assumptions remain visible.
- Recommendations are manual actions only.
- Stale or low-evidence guidance should be delayed rather than presented as certain.
- Readiness score separates travel, combat, progression, legendary, and group PvE.
- Missing account facts are shown as assumptions instead of invented character or unlock facts.
- Full reports include evidence, data freshness, assumptions, and safety boundaries.
