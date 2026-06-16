# MVP 0.4.4 Patch Note Structured Summaries

## Scope

This milestone generates structured Knowledge Base draft summaries for recent official patch-note PDFs.

## Implemented

- Added a reusable patch-note summarizer:
  - `src/gw2radar/kb_pdf/patch_note_summarizer.py`
- Generated structured draft summaries from `data/kb/pdf_inventory.csv`.
- Covered P2 recent patch notes:
  - 2024: 18 files
  - 2025: 19 files
  - 2026: 8 files
- Output directory:
  - `docs/knowledge_base/patch_notes/2024/`
  - `docs/knowledge_base/patch_notes/2025/`
  - `docs/knowledge_base/patch_notes/2026/`

## Structured Fields

Each generated patch note includes:

- `patch_id`
- `date`
- `source_pdf`
- `evidence_id`
- `changed_professions`
- `changed_skills`
- `changed_traits`
- `changed_items`
- `changed_rewards`
- `affected_systems`
- `possible_build_impact`
- `possible_market_impact`
- `confidence`
- `review_status`

## Boundaries

- Generated files are draft source stubs.
- Full patch-note text is not copied.
- Impact fields remain `needs_manual_review` until a reviewer validates source details.
- Draft patch notes do not drive high-priority recommendations.

## Verification

- `tests/test_patch_note_summarizer.py`
- Existing PDF classifier and patch inventory tests
- KB directory loader tests
