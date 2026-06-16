# MVP 0.4.6 Patch Impact Review Assistant

## Scope

This milestone turns generated patch-note draft summaries into an auditable review workflow.

Implemented:

- List patch draft summaries by year/date.
- Filter pending patch impact reviews.
- Store manual affected systems, build impact, and market impact annotations.
- Generate reviewed but disabled KnowledgeRule candidates from reviewed patch impact records.
- Expose the workflow through `/api/v1/kb/patch-impact/*`.

## Safety Boundary

- Draft patch summaries are not promoted automatically.
- KnowledgeRule candidates are returned as candidates only and are `enabled=false`.
- Candidate rules require a saved reviewed patch impact record.
- Original PDF source text is not copied into review artifacts.

## Data

- Input summaries: `docs/knowledge_base/patch_notes/{year}/{date}.md`
- Review store: `data/kb/patch_impact_reviews.jsonl`

## Validation

- Unit tests cover list, pending filter, review persistence, candidate generation, and validation guards.
- API tests cover draft listing, review write, and rule candidate retrieval.
