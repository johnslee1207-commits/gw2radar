# MVP 0.3.6 Creator & Community Intelligence Console

Date: 2026-06-16

## Scope

P11 adds a creator/community intelligence lane on top of the existing commercial report stack.

Implemented deliverables:

- community signal import;
- topic trend aggregation;
- question clustering;
- guide gap analysis;
- content opportunity planning;
- creator intelligence Markdown report;
- source attribution preservation;
- no mass-copy policy enforcement;
- private community source authorization guard;
- versioned `/api/v1/creator` routes.

## API Surface

- `POST /api/v1/creator/signals/import`
- `GET /api/v1/creator/topics`
- `GET /api/v1/creator/opportunities`
- `POST /api/v1/creator/report`

## Safety Boundaries

- Stores summaries and source links only.
- Does not store third-party full text or long raw copied context.
- Preserves source URLs in trend, opportunity, and report output.
- Treats unverified community-derived claims as low-confidence.
- Requires explicit authorization before importing private Discord signals.

## Persistence

Added `community_signals` with:

- source type and source URL;
- title, summary, topic, audience segment, signal kind;
- confidence and verified flags;
- private-source authorization flag;
- creation timestamp.

## Verification

Targeted P11 tests:

- `tests/test_community_signal.py`
- `tests/test_topic_trend.py`
- `tests/test_guide_gap.py`
- `tests/test_content_opportunity.py`
- `tests/test_creator_report.py`
- `tests/test_source_attribution.py`
- `tests/test_no_mass_copy.py`
- `tests/test_creator_api.py`

Result: 11 targeted tests passed.

## Known Limitations

- No live ingestion from public forums, Reddit, YouTube, or Discord.
- No automated verification against official GW2 sources yet.
- Opportunity scoring is deterministic and simple; richer ranking can use market/build/guild signals later.
- Creator report is direct Markdown, not yet a paid report artifact product.
