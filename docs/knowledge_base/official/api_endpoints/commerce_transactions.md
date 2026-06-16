---
title: GW2 API endpoint /v2/commerce/transactions
domain: official
content_type: source_note
summary: Initial endpoint summary for commerce transaction history, reserved for later-stage account-authorized market features.
source_refs:
linked_entities: api_endpoint:/v2/commerce/transactions
linked_actions: VALIDATE_API_SCOPE
confidence: 0.8
review_status: draft
---

# GW2 API Endpoint /v2/commerce/transactions

- source_id: `source:gw2api:commerce_transactions`
- source_url: `https://wiki.guildwars2.com/wiki/API:2/commerce/transactions`
- endpoint: `/v2/commerce/transactions`
- method: `GET`
- requires_credential: `true`
- required_scopes: `tradingpost`
- graph_layer: `private_authorized_account_state`
- cache_ttl: `gateway-managed`
- batch_supported: `verify_from_source`
- primary_entities: `api_endpoint:/v2/commerce/transactions`
- primary_actions: `VALIDATE_API_SCOPE`

Policy:

- not part of the MVP market feature path;
- no automated trading;
- no guaranteed-profit language;
- use only after explicit entitlement and privacy review.
