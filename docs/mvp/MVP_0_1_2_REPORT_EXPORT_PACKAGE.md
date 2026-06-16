# MVP 0.1.2 Report Export Package

MVP 0.1.2 turns the current legendary-goal intelligence loop into a deterministic local delivery package.

## Package Contents

For each goal, the exporter writes:

- `goal_report.md`
- `goal_gap.csv`
- `recommended_actions.csv`
- `package_manifest.json`

Default API output root:

```text
outputs/{safe_goal_id}/
```

The `outputs/` directory is ignored by git because it contains generated artifacts.

## Manifest Contract

The manifest uses:

```text
schema_version = gw2radar.export_package.v1
package_type = legendary_goal_report
recommendation_boundary = informational_manual_actions_only
```

The manifest must list all generated files, including `package_manifest.json`.

## API

```http
POST /reports/{goal_id}/export-package
```

This endpoint generates the package from the current graph state. It does not call the GW2 API, automate gameplay, automate trading, or interact with the game client.

## Verification

- `tests/test_export_package.py`
- `python harness/run_smoke.py`
