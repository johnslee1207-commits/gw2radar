# MVP 0.4.2 KB-backed Paid Report Artifacts

## Scope

This milestone connects reviewed Knowledge Base rules to the paid report artifact pipeline.

## Implemented

- Paid report generation accepts an explicit `knowledge_backed` mode.
- KB-backed paid reports render reviewed rule explanations into the Markdown artifact.
- Report artifact manifests include a `knowledge_base` block with:
  - whether KB explanations were enabled;
  - reviewed/enabled rule count;
  - the reviewed-rule boundary.
- The paid report API loads persisted KB rules only when `knowledge_backed` is requested.
- Existing entitlement checks still gate paid artifact generation.

## Boundaries

- Draft, deprecated, disabled, or action-mismatched KB rules do not produce explanations.
- KB explanations are informational and do not automate gameplay.
- Report artifacts preserve the existing privacy boundary: no secrets and no unredacted private payloads.
- This milestone does not add real payments, billing portals, or multi-tenant SaaS behavior.

## Verification

- `tests/test_kb_paid_report_artifact.py`
- Existing paid report API and artifact tests
