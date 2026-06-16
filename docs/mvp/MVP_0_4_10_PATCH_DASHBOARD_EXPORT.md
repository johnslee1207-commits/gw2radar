# MVP 0.4.10 Patch Dashboard Export

## Scope

This milestone adds deterministic Markdown and CSV exports for the patch review dashboard queue.

Implemented:

- Render dashboard queue items as Markdown for admin preview.
- Render dashboard queue items as CSV for review tracking and frontend debugging.
- Expose exports through `/api/v1/kb/patch-impact/dashboard/export`.
- Keep export rendering side-effect free; it returns strings and does not write runtime files.

## API

`GET /api/v1/kb/patch-impact/dashboard/export?year=2026&format=markdown`

`GET /api/v1/kb/patch-impact/dashboard/export?year=2026&format=csv`

## Safety Boundary

- Export is read-only.
- It does not promote reviews, persist rules, or enable rules.
- It references source PDFs and evidence IDs but does not copy raw PDF text.

## Validation

- Unit tests verify deterministic Markdown and CSV structure.
- API tests verify media types and unsupported format rejection.
