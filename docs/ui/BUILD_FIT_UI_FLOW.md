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
9. Preview and import `build_upgrade_effects` when reviewed KB evidence should explain upgrade families.
10. Enable selected reviewed upgrade rules.
11. Re-run fit score and confirm reviewed KB evidence appears only for enabled rules.
12. Generate build report.

## Output Expectations

- Fit score separates gear, unlock, affordability, mode, difficulty, and patch freshness.
- Reusable and missing gear are separated.
- Budget alternatives are suggestions, not meta guarantees.
- Source attribution is preserved.
- Synced official API snapshots must be labeled as synced private data and remain advisory.
- Synced official API equipment should use public item/stat metadata enrichment when available and keep id/Unknown fallbacks when metadata is missing.
- Official upgrade metadata should classify runes and sigils as separate advisory gear entries; relics should retain a relic category when the API exposes the slot/type.
- Rune, sigil, and relic entries should receive conservative effect-family evaluation such as power damage, condition damage, boon support, healing support, defensive survival, or unknown. These labels are manual-review hints, not meta guarantees.
- Upgrade effect labels should cite reviewed and enabled KB rules when matching evidence exists. If no reviewed evidence matches, the output must explicitly remain heuristic instead of inventing a source.
- The upgrade rule pack UI must keep imported rules disabled until a reviewer enables a selected rule.
- Manual sample character snapshots must keep assumptions visible and must not be represented as synced ArenaNet equipment.
