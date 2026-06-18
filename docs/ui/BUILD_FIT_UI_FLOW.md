# Build Fit Advisor UI Flow

## User Intent

A player wants to know whether their account can play a build, what gear is reusable, what is missing, and whether a cheaper transition path exists.

## Flow

1. Open `Build Fit`.
2. Import a structured build with profession, specialization, role, mode, freshness, and estimated cost.
3. List builds or use the imported build id.
4. Load character snapshots.
5. Choose a synced official API character snapshot when available, use manual samples as fallback, or stay in manual fields mode.
6. Run fit score.
7. Run transition plan.
8. Check patch freshness.
9. Generate build report.

## Output Expectations

- Fit score separates gear, unlock, affordability, mode, difficulty, and patch freshness.
- Reusable and missing gear are separated.
- Budget alternatives are suggestions, not meta guarantees.
- Source attribution is preserved.
- Synced official API snapshots must be labeled as synced private data and remain advisory.
- Manual sample character snapshots must keep assumptions visible and must not be represented as synced ArenaNet equipment.
