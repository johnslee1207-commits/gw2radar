# MVP 0.3.0 Paid Report Engine

Date: 2026-06-16

## Roadmap Assessment

The commercial roadmap defines P6-P14. Based on the current implementation maturity, the correct first commercial milestone is P6 Paid Report Engine because P7-P11 all need a report product, entitlement, export job, and artifact contract.

Current prerequisites are satisfied for an MVP implementation:

- durable refresh queue exists;
- official API gateway/client boundary exists;
- account sync product routes exist;
- public static refresh planner exists;
- production security foundation exists.

## Implemented P6 Scope

- `ReportProduct` model and default product catalog.
- `ReportEntitlement` model and mock unlock flow.
- `ReportExportJob` model with queued, processing, succeeded, failed states.
- Free preview rendering mode.
- Paid full report rendering mode.
- Markdown and HTML export support.
- PDF export interface stub.
- Report artifact manifest.
- Versioned commercial report API routes:

```http
GET  /api/v1/reports/products
POST /api/v1/reports/preview
POST /api/v1/reports/generate
GET  /api/v1/reports/jobs/{job_id}
GET  /api/v1/reports/artifacts/{artifact_id}
```

## Commercial Boundaries

- Real payment provider integration is deferred to P12.
- P6 uses entitlements, but tests create entitlements directly as a payment abstraction stand-in.
- Free preview hides paid-only missing-material detail.
- Full report remains evidence-backed and recommendation-only.
- Artifacts do not include API keys or unredacted private payloads.

## Verification

Added tests:

- `tests/test_report_product_model.py`;
- `tests/test_report_entitlement.py`;
- `tests/test_free_report_preview.py`;
- `tests/test_paid_report_full.py`;
- `tests/test_report_export_job.py`;
- `tests/test_report_no_secret_leakage.py`;
- `tests/test_paid_report_api_routes.py`.

Required verification:

```text
python -m pytest
python harness/run_smoke.py
python harness/run_sync_smoke.py
python -m alembic upgrade head
```

## Next Milestone

P7 Legendary Planner Pro:

- goal portfolio;
- shared requirement inference;
- multi-goal do-not-sell policy;
- cheap and fast path planning;
- daily and weekly legendary report.
