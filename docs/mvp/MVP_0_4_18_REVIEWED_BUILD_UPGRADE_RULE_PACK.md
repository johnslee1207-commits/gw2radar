# MVP 0.4.18 Reviewed Build Upgrade Rule Pack

Date: 2026-06-18

## Scope

This milestone turns Build Fit upgrade-effect heuristics into operator-reviewable KB rule content.

## Implemented

- Added `build_upgrade_effects` to the domain rule pack registry.
- Added reviewed but disabled KnowledgeRule candidates for:
  - `power_damage`;
  - `condition_damage`;
  - `boon_support`;
  - `healing_support`;
  - `defensive_survival`.
- Reused the existing KB rule pack preview/import APIs:

```http
GET  /api/v1/kb/rule-packs
GET  /api/v1/kb/rule-packs/build_upgrade_effects
POST /api/v1/kb/rule-packs/build_upgrade_effects/import
POST /api/v1/kb/rules/{rule_id}/enable
```

## Safety Boundaries

- Rule pack import requires explicit confirmation.
- Imported rules remain `enabled=false`.
- Build Fit evidence uses only reviewed and enabled rules.
- Disabled rules do not change upgrade-effect explanations.
- Upgrade-effect labels are manual-review hints, not meta guarantees or automatic gear changes.

## Verification

Added and updated tests:

- `tests/test_kb_domain_rule_packs.py`;
- `tests/test_upgrade_effect_evaluation.py`;
- `tests/test_build_fit_api.py`.

Required verification:

```text
pytest tests/test_kb_domain_rule_packs.py tests/test_upgrade_effect_evaluation.py tests/test_build_fit_api.py -q -s
python harness/run_smoke.py
pytest -q -s
```

## Next Milestone

P19 Build Upgrade Evidence Admin Flow:

- Admin preview for imported upgrade-effect rules;
- bulk enable/re-disable workflow with reviewer metadata;
- report manifest evidence chain for Build Fit upgrade effects.
