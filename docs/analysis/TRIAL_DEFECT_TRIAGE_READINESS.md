# Real User Trial Readiness

- Schema: gw2radar.trial_readiness_checklist.v1
- Status: ready_for_user_trial

## Checklist

| Item | Endpoint | Expected Result | Operator Note |
| --- | --- | --- | --- |
| Connect GW2 API key | `/account/api-key/status` | masked configured key status or clear missing-key action | Never ask the player to send the raw key. |
| Inspect permissions | `/account/api-key/permissions` | required permission readiness or missing permission list | Missing permissions should produce limited mode, not silent empty results. |
| Run connection diagnostic | `/account/diagnostic` | step-level status for key, permission, sync, private layer, and Build Fit bridge | Use diagnostic next_actions before asking for a support bundle. |
| Generate privacy-safe debug bundle | `/account/debug-bundle` | metadata-only bundle with no raw key or private payload | Bundle can be reviewed and audited through the support workflow. |
| Triage empty or invisible result | `/api/v1/ops/trial/defect-triage` | classification, severity, operator actions, and evidence needed | Use when users report no visible output after connecting a valid key. |

## Defect Intake Channels

- privacy-safe account debug bundle review
- support review UI audit
- operator release packet verification
- GitHub issue or commit-linked defect note

## Safety Boundaries

- local-first mode remains the default
- no raw secret or private payload export
- no automated gameplay action
- no automated trading instruction
- no guaranteed outcome claim

## Next Priority

Run real user trial on account connection and capture only privacy-safe defect metadata.


---

# Trial Defect Triage Dashboard

- Schema: gw2radar.trial_defect_dashboard.v1
- Status: ready_for_user_trial
- Stop-line policy: Do not add broad new phases during trial; fix reproducible defects and diagnostics gaps.

## Supported Classifications

- raw_key_shared
- api_key_not_saved
- missing_permissions
- sync_not_started
- sync_pending_or_failed
- private_layer_empty
- character_snapshot_empty
- result_generation_empty
- ui_flow_incomplete
- no_defect_detected

## Primary Trial Entrypoints

- `/account/api-key/status`
- `/account/api-key/permissions`
- `/account/diagnostic`
- `/account/debug-bundle`
- `/api/v1/ops/trial/defect-triage`

## Next Priority

Use real trial reports to prioritize API key diagnostics, empty-state UX, and support bundle clarity.
