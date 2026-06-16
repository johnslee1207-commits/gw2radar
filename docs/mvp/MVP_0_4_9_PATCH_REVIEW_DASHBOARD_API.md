# MVP 0.4.9 Patch Review Dashboard API

## Scope

This milestone adds a read-only dashboard API that aggregates patch review lifecycle state for frontend review queues.

Implemented:

- Aggregate patch draft summaries, review records, persisted rules, enabled rules, and audit events.
- Expose a single queue view through `/api/v1/kb/patch-impact/dashboard`.
- Support optional `year` filtering.
- Return lifecycle counts for quick dashboard tabs.

## Lifecycle Status

Each patch item is classified as:

- `draft`
- `needs_update`
- `reviewed`
- `persisted`
- `enabled`

The most advanced state wins. For example, a patch with at least one enabled rule is `enabled`.

## API Shape

`GET /api/v1/kb/patch-impact/dashboard?year=2026`

Returns:

- `count`
- `lifecycle_counts`
- `items[]`

Each item includes:

- patch identity: `patch_id`, `date`, `year`, `title`
- source evidence: `source_pdf`, `evidence_id`
- review fields: `review_status`, `affected_systems`, build/market impact
- lifecycle counts: candidate, persisted, enabled, audit events
- audit summary: action counts, latest reviewer, latest audit timestamp
- linked `rule_ids`

## Safety Boundary

- Dashboard API is read-only.
- It does not promote reviews, persist candidates, enable rules, or change ranking.
- It does not copy raw PDF text into responses.

## Validation

- Service tests cover draft, reviewed, persisted, and enabled aggregation.
- API tests verify dashboard status, counts, and audit action summaries.
