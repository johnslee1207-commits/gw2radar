---
title: GW2 API endpoint /v2/characters/:id/equipmenttabs
domain: official
content_type: source_note
summary: Initial endpoint summary for character equipment tabs; verify behavior against the official source before promotion to reviewed.
source_refs:
linked_entities: api_endpoint:/v2/characters/:id/equipmenttabs
linked_actions: INGEST_SOURCE, VALIDATE_API_SCOPE
confidence: 0.85
review_status: draft
---

# GW2 API Endpoint /v2/characters/:id/equipmenttabs

- source_id: `source:gw2api:character_equipmenttabs`
- source_url: `https://wiki.guildwars2.com/wiki/API:2/characters/:id/equipmenttabs`
- endpoint: `/v2/characters/:id/equipmenttabs`
- method: `GET`
- requires_credential: `true`
- required_scopes: `characters`
- graph_layer: `private_authorized_account_state`
- cache_ttl: `gateway-managed`
- batch_supported: `verify_from_source`
- primary_entities: `api_endpoint:/v2/characters/:id/equipmenttabs`
- primary_actions: `INGEST_SOURCE`, `VALIDATE_API_SCOPE`

Use this endpoint for Build Fit and Gear Transition review after scope validation.
