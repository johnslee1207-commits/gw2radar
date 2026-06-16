---
title: GW2 API endpoint /v2/commerce/delivery
domain: official
content_type: source_note
summary: Initial endpoint summary for commerce delivery state, reserved for later-stage account-authorized market features.
source_refs:
linked_entities: api_endpoint:/v2/commerce/delivery
linked_actions: VALIDATE_API_SCOPE
confidence: 0.8
review_status: draft
---

# GW2 API Endpoint /v2/commerce/delivery

- source_id: `source:gw2api:commerce_delivery`
- source_url: `https://wiki.guildwars2.com/wiki/API:2/commerce/delivery`
- endpoint: `/v2/commerce/delivery`
- method: `GET`
- requires_credential: `true`
- required_scopes: `tradingpost`
- graph_layer: `private_authorized_account_state`
- cache_ttl: `gateway-managed`
- batch_supported: `verify_from_source`
- primary_entities: `api_endpoint:/v2/commerce/delivery`
- primary_actions: `VALIDATE_API_SCOPE`

Policy:

- not part of the MVP market feature path;
- no automated trading;
- no guaranteed-profit language;
- use only after explicit entitlement and privacy review.
