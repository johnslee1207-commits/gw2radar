# MVP 0.4.3 KB Report Quality And Source Gaps

## Scope

This milestone adds Knowledge Base report quality scoring and completes the next official-source gap slice.

## Implemented

- KB-backed reports now include a Knowledge Base quality section.
- KB quality scoring reports:
  - total recommendation actions;
  - explained actions;
  - unexplained action IDs;
  - matched reviewed rule count;
  - reviewed/enabled rule count;
  - coverage percentage;
  - average explanation confidence;
  - low-confidence explanation warnings;
  - quality label.
- Paid report artifacts include a `knowledge_base.quality` manifest summary.
- API route added:
  - `GET /api/v1/kb/goals/{goal_id}/report-quality`
- Official source gap files added for:
  - official news source;
  - official patch-note source;
  - authenticated endpoint index;
  - character equipment tabs;
  - itemstats;
  - render service;
  - commerce transactions;
  - commerce delivery.

## Boundaries

- Quality scoring is advisory and does not change action generation.
- Draft KB content still cannot drive high-priority rules.
- Source files remain summaries and links, not full-page mirrors.
- Private/account-authorized endpoint notes stay marked for private graph handling.

## Verification

- `tests/test_kb_report_quality.py`
- Existing KB-backed report and paid artifact tests
- KB directory loader tests
