---
title: Authenticated endpoint source index
domain: official
content_type: source_note
summary: Authenticated endpoint references define which GW2 API resources require user authorization and must stay in private graph layers.
source_refs:
linked_entities: gw2:system:authenticated_endpoints
linked_actions: VALIDATE_API_SCOPE, SYNC_ACCOUNT_SNAPSHOT
confidence: 0.9
review_status: draft
---

# Authenticated Endpoint Source Index

- source_id: `source:gw2wiki:authenticated_endpoints`
- source_url: `https://wiki.guildwars2.com/wiki/Category:Authenticated_endpoint`
- allowed_use: `summary_and_reference`
- crawl_policy: `manual_or_low_frequency`

Policy:

- validate authorization scopes before account-state synchronization;
- keep account-scoped responses in private graph layers;
- publish only derived, privacy-safe summaries to reports;
- never store raw credentials or raw account payloads in public KB content.

Initial endpoint families:

- `/v2/account`
- `/v2/characters`
- `/v2/account/wallet`
- `/v2/account/bank`
- `/v2/account/achievements`
- `/v2/commerce/transactions`
- `/v2/commerce/delivery`
- `/v2/characters/:id/equipmenttabs`
