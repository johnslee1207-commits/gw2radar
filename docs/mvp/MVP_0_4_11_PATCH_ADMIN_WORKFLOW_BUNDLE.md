# MVP 0.4.11 Patch Admin Workflow Bundle

## Scope

This milestone bundles patch review admin actions into a frontend-friendly workflow API.

Implemented:

- Review a patch impact record.
- Persist reviewed rule candidates.
- Enable selected reviewed rules.
- Return updated dashboard state.
- Return patch audit events.
- Optionally include deterministic Markdown and CSV dashboard exports.

## API

`POST /api/v1/kb/patch-impact/admin/workflow`

Supported request fields:

- `year`
- `patch_id`
- `review`
- `persist_confirmed`
- `enable_rule_ids`
- `enable_confirmed`
- `reviewer`
- `include_markdown_export`
- `include_csv_export`

## Safety Boundary

- The workflow API does not bypass confirmation gates.
- Persisting candidates still requires `persist_confirmed=true`.
- Enabling rules still requires `enable_confirmed=true`.
- Exports are returned as strings and do not write runtime files.
- Raw PDF text is not copied into responses.

## Validation

- API tests cover review + persist + export in one call.
- API tests cover enable + audit refresh in one call.
- API tests verify blocked persist/enable requests remain blocked.
