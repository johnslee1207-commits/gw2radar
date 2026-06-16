# MVP 0.4.5 Official News Source Processing

## Scope

This milestone processes locally downloaded official Guild Wars 2 news PDFs as Knowledge Base source artifacts.

## Implemented

- Added official news PDF classification:
  - category: `official_news`
  - priority: `P2`
  - source directory: `docs/knowledge_base/_sources/pdf/news/`
- Updated PDF inventory and evidence generation to include official news PDFs.
- Added reusable official news summarizer:
  - `src/gw2radar/kb_pdf/official_news_summarizer.py`
- Generated 44 official news draft summaries:
  - `docs/knowledge_base/news/official/*.md`
- Updated PDF source processing report and source coverage analysis.

## Structured Fields

Each official news draft includes:

- `news_id`
- `source_type`
- `source_pdf`
- `evidence_id`
- `affected_systems`
- `possible_product_context`
- `confidence`
- `review_status`

## Boundaries

- Generated news files are draft source stubs.
- Full official news text is not copied.
- Product context fields remain `needs_manual_review` until reviewed.
- News PDFs remain ignored source artifacts; only inventory, evidence metadata, and summary stubs are committed.

## Verification

- `tests/test_official_news_summarizer.py`
- PDF classifier, inventory, evidence, and KB directory loader tests
