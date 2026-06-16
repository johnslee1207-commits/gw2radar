# MVP 0.3.8 KB Repository + Markdown Loader + API Surface

Date: 2026-06-16

## Scope

P2 expands the Knowledge Base foundation into a usable local subsystem.

Implemented deliverables:

- KB article search over title, summary, body, linked entities, and linked actions;
- Markdown-backed article loader with simple local front matter;
- versioned KB API routes;
- review and deprecate API actions;
- safety-preserving article creation through the API.

## API Surface

- `POST /api/v1/kb/articles`
- `GET /api/v1/kb/articles`
- `GET /api/v1/kb/articles/{kb_id}`
- `POST /api/v1/kb/articles/{kb_id}/review`
- `POST /api/v1/kb/articles/{kb_id}/deprecate`
- `GET /api/v1/kb/search`

## Markdown Loader

The loader accepts local `.md` files only. Files must start with simple front matter:

```text
---
title: Mystic Clover planning note
domain: legendary
content_type: summary
summary: Concise source-linked summary.
source_refs: kb_source_...
linked_entities: gw2:item:mystic_clover
linked_actions: do_daily
confidence: 0.8
review_status: draft
---
Markdown body.
```

No remote fetching, scraping, execution, or HTML trust is introduced.

## Safety Boundaries

- Existing KB model safety checks remain active for API and loader input.
- Article creation rejects private player data markers and mass-copy markers.
- Search excludes deprecated articles by default.
- Review/deprecate operations are explicit state transitions.

## Verification

Targeted tests:

- `tests/test_kb_markdown_loader.py`
- `tests/test_kb_search.py`
- `tests/test_kb_api.py`

Result: targeted KB P2 tests passed.

## Known Limitations

- Source registry API is not exposed yet.
- Search is simple deterministic substring search, not vector search.
- Markdown loader handles intentionally simple front matter only.
- No RAG or automatic rule distillation is implemented in P2.

## Next Priority

P3: KB Source Registry API + Domain Seed Loader.
