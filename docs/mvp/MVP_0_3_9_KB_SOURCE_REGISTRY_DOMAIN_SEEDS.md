# MVP 0.3.9 KB Source Registry API + Domain Seed Loader

Date: 2026-06-16

## Scope

P3 makes the Knowledge Base usable as a seeded local knowledge system.

Implemented deliverables:

- source registry API;
- source listing and lookup;
- local directory-backed Markdown bulk loader;
- minimal domain seed structure under `docs/knowledge_base`;
- seed articles for official, legendary, returner, build, market, guild, and creator domains;
- loader guard that skips source registry documents;
- tests for source API, directory loading, and seed coverage.

## API Surface

- `POST /api/v1/kb/sources`
- `GET /api/v1/kb/sources`
- `GET /api/v1/kb/sources/{source_id}`
- `POST /api/v1/kb/load-directory`

The P2 article API remains available.

## Seed Domains

Minimal seed articles now exist for:

- `official`
- `legendary`
- `returner`
- `build`
- `market`
- `guild`
- `creator`

These seeds are local summaries and policy notes only. They do not contain copied third-party full text, credentials, or account-state payloads.

## Safety Boundaries

- The loader accepts local Markdown only.
- Source registry docs are not loaded as KB articles.
- KB model safety checks still reject mass-copy markers and private data markers.
- Community/creator draft content remains low confidence until reviewed.

## Verification

Targeted tests:

- `tests/test_kb_source_api.py`
- `tests/test_kb_directory_loader.py`
- `tests/test_kb_domain_seed_loader.py`

Result: P3 targeted tests passed.

## Known Limitations

- No source registry seed importer yet.
- No vector search or RAG layer.
- No automatic rule distillation from seed articles.
- Seeds are intentionally concise and local; they are not a full game guide corpus.

## Next Priority

P4: KB Entity Linker + Rule Distiller Integration.
