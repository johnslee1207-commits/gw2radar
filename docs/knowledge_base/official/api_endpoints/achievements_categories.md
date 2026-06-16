---
title: GW2 API endpoint /v2/achievements/categories
domain: official
content_type: source_note
summary: Initial endpoint summary for /v2/achievements/categories; verify behavior against the source PDF before promotion to reviewed.
source_refs:
linked_entities: api_endpoint:/v2/achievements/categories
linked_actions: INGEST_SOURCE, VALIDATE_API_SCOPE
confidence: 0.9
review_status: draft
---

# GW2 API Endpoint /v2/achievements/categories

- endpoint: `/v2/achievements/categories`
- method: `GET`
- requires_api_key: `false`
- required_scopes: `none`
- public_or_private_graph_layer: `public_game_data`
- cache_ttl: `gateway-managed`
- batch_supported: `verify_from_source`
- primary_entities: `api_endpoint:/v2/achievements/categories`
- primary_actions: `INGEST_SOURCE`, `VALIDATE_API_SCOPE`
- error_handling_notes: `Use governed gateway behavior and preserve evidence metadata.`
- source_pdf: `docs/knowledge_base/_sources/pdf/official_api/endpoints/API_2_achievements_categories - Guild Wars 2 Wiki (GW2W).pdf`
- evidence_id: `evidence:pdf:api_endpoint:achievements_categories`

Processing note: this is an initial structured summary and intentionally avoids full-text PDF copying.
