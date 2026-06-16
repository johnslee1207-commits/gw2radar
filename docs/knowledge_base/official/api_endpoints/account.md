---
title: GW2 API endpoint /v2/account
domain: official
content_type: source_note
summary: Initial endpoint summary for /v2/account; verify behavior against the source PDF before promotion to reviewed.
source_refs:
linked_entities: api_endpoint:/v2/account
linked_actions: INGEST_SOURCE, VALIDATE_API_SCOPE
confidence: 0.9
review_status: draft
---

# GW2 API Endpoint /v2/account

- endpoint: `/v2/account`
- method: `GET`
- requires_api_key: `true`
- required_scopes: `account`
- public_or_private_graph_layer: `private_player_state`
- cache_ttl: `gateway-managed`
- batch_supported: `verify_from_source`
- primary_entities: `api_endpoint:/v2/account`
- primary_actions: `INGEST_SOURCE`, `VALIDATE_API_SCOPE`
- error_handling_notes: `Use governed gateway behavior and preserve evidence metadata.`
- source_pdf: `docs/knowledge_base/_sources/pdf/official_api/endpoints/API_2_account - Guild Wars 2 Wiki (GW2W).pdf`
- evidence_id: `evidence:pdf:api_endpoint:account`

Processing note: this is an initial structured summary and intentionally avoids full-text PDF copying.
