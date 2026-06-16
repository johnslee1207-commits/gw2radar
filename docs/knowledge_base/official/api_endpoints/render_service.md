---
title: GW2 API render service summary
domain: official
content_type: source_note
summary: Initial source summary for the GW2 render service used to reference official icons and UI assets.
source_refs:
linked_entities: api_endpoint:render_service
linked_actions: INGEST_SOURCE
confidence: 0.85
review_status: draft
---

# GW2 API Render Service

- source_id: `source:gw2api:render_service`
- source_url: `https://wiki.guildwars2.com/wiki/API:Render_service`
- endpoint_family: `render service`
- method: `GET`
- requires_credential: `false`
- required_scopes: `none`
- graph_layer: `public_game_data`
- cache_ttl: `public-static-refresh`
- primary_entities: `api_endpoint:render_service`
- primary_actions: `INGEST_SOURCE`

Use this source for icons and UI resources where permitted by source policy.
