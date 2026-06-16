# MVP 0.4.0 KB Entity Linker + Rule Distiller

Date: 2026-06-16

## Scope

P4 connects Knowledge Base records to the existing ontology and graph reasoning substrate.

Implemented deliverables:

- KB entity/action link validation;
- graph-backed validation for concrete `linked_entities`;
- concept entity support for KB-only concepts such as `gw2:system:*` and `gw2:segment:*`;
- strict `linked_actions` validation against `ActionType`;
- rule distillation from reviewed KB rule articles into persisted `KnowledgeRule` records;
- versioned API endpoints for link validation and rule distillation.

## API Surface

- `POST /api/v1/kb/articles/{kb_id}/validate-links`
- `POST /api/v1/kb/articles/{kb_id}/distill-rule`

## Rule Distillation Contract

Only articles that satisfy all of these conditions can become `KnowledgeRule` records:

- `content_type = rule`;
- `review_status = reviewed`;
- at least one valid linked action;
- linked action exists in the `ActionType` ontology;
- existing KB safety rules still pass.

Distilled rules use:

- article title as rule name;
- article domain as rule domain;
- article summary as recommendation;
- first linked action as action type;
- linked entities as condition context;
- article source refs as evidence refs.

## Safety Boundaries

- Draft KB articles cannot be distilled.
- Non-rule articles cannot be distilled.
- Invalid action strings cannot become rule action types.
- Missing graph entities are reported by validation instead of silently accepted.
- KB-only concept entities are separated from graph-backed concrete entities.

## Verification

Targeted tests:

- `tests/test_kb_entity_linker.py`
- `tests/test_kb_rule_distiller_integration.py`
- `tests/test_kb_linker_distiller_api.py`

Result: P4 targeted tests passed.

## Known Limitations

- Link validation is deterministic and schema-based, not semantic fuzzy matching.
- Concept entities are allowed by prefix and are not yet persisted into the graph.
- Rule distillation is template-based; no LLM/RAG extraction is used.
- Distilled rules do not yet feed action ranking automatically.

## Next Priority

P5: KB-backed Recommendation Explanation Integration.
