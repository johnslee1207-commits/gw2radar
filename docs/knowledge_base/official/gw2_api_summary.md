---
title: GW2 API governed access summary
domain: official
content_type: source_note
summary: GW2Radar uses the official API through the governed gateway and records source-linked evidence for reportable facts.
linked_entities: gw2:system:official_api
linked_actions: 
confidence: 0.95
review_status: reviewed
---
GW2Radar treats official API data as high-trust source material when accessed through the project gateway.

Operational notes:

- use the gateway for external API access;
- preserve endpoint, timestamp, and confidence metadata;
- do not log or store raw credentials in KB content;
- separate public game data from authorized account-state evidence.
