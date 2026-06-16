---
title: Guild readiness member privacy policy
domain: guild
content_type: rule
summary: Guild readiness reports should show consent-based summaries only and must not expose raw account payloads.
linked_entities: gw2:system:guild_readiness
linked_actions: generate_weekly_plan
confidence: 0.85
review_status: reviewed
---
Guild Readiness Console should help teams coordinate without leaking member account details.

Policy notes:

- require consent before using member readiness data;
- show readiness bands and role coverage summaries;
- do not expose raw inventory, wallet, bank, credentials, or account payloads;
- remove members from readiness calculations when consent is revoked.
