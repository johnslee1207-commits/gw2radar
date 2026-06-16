---
title: GW2 API endpoint /v2/itemstats
domain: official
content_type: source_note
summary: Initial endpoint summary for item stat metadata used by gear and build-fit reasoning.
source_refs:
linked_entities: api_endpoint:/v2/itemstats
linked_actions: INGEST_SOURCE
confidence: 0.85
review_status: draft
---

# GW2 API Endpoint /v2/itemstats

- source_id: `source:gw2api:itemstats`
- source_url: `https://wiki.guildwars2.com/wiki/API:2/itemstats`
- endpoint: `/v2/itemstats`
- method: `GET`
- requires_credential: `false`
- required_scopes: `none`
- graph_layer: `public_game_data`
- cache_ttl: `public-static-refresh`
- batch_supported: `verify_from_source`
- primary_entities: `api_endpoint:/v2/itemstats`
- primary_actions: `INGEST_SOURCE`

Use this endpoint to support gear stat lookup and Build Fit scoring.
