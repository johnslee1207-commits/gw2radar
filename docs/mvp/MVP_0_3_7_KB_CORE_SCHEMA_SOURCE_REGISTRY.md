# MVP 0.3.7 KB Core Schema + Source Registry

Date: 2026-06-16

## Scope

P1 starts the Knowledge Base subsystem with core schemas, persistence, and safety boundaries.

Implemented deliverables:

- `SourceRegistry` model;
- `KnowledgeArticle` model;
- `KnowledgeChunk` model;
- `KnowledgeRule` model;
- `KnowledgeReviewStatus`;
- SQLite persistence tables and Alembic migration;
- repository functions for sources, articles, chunks, rules, review, and deprecation;
- safety checks for no mass-copy content;
- safety checks preventing private player data in KB content;
- guard preventing unreviewed KB rules from driving high-priority actions.

## Persistence

Added tables:

- `knowledge_sources`
- `knowledge_articles`
- `knowledge_chunks`
- `knowledge_rules`

Migration:

- `0014_add_knowledge_base_tables.py`

## Safety Boundaries

- KB stores summaries, rules, source links, and reviewed explanations.
- KB must not store third-party full-text content.
- KB must not store API keys, private inventory, bank contents, account identifiers, or private player state.
- Community/creator draft knowledge is capped to low confidence until reviewed.
- Draft or unreviewed rules cannot produce high-priority action deltas.

## Verification

Targeted tests:

- `tests/test_kb_article_model.py`
- `tests/test_kb_source_registry.py`
- `tests/test_kb_repository.py`
- `tests/test_kb_review_status.py`
- `tests/test_kb_rule_distillation.py`
- `tests/test_kb_entity_linking.py`
- `tests/test_kb_no_private_data_leakage.py`
- `tests/test_kb_no_unreviewed_high_priority_action.py`

Result: 12 targeted tests passed.

Full quality gate:

- `python -m pytest`: 165 passed
- `python harness/run_smoke.py`: PASS
- `python harness/run_sync_smoke.py`: PASS
- `python -m alembic upgrade head`: PASS

## Known Limitations

- No KB API routes yet.
- No Markdown-backed KB loader yet.
- No search or RAG layer yet.
- No automated rule distillation from articles yet; P1 only adds the rule data contract and safety guard.

## Next Priority

P2: KB Repository + Markdown Loader + API Surface.
