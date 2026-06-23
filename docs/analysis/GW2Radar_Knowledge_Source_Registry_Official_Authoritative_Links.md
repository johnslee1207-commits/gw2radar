# GW2Radar Knowledge Source Registry — Official & Authoritative Links

```text
Document ID: GW2RADAR_KNOWLEDGE_SOURCE_REGISTRY_OFFICIAL_AUTHORITATIVE_LINKS
Project: GW2Radar
Version: v0.1
Status: Source Registry Draft
Target Directory:
  docs/knowledge_base/source_registry/
Purpose:
  Provide the first batch of official, authoritative, and high-value public knowledge sources
  for manual collection, evidence registration, KB summarization, and later graph linking.
```

---

## 0. Purpose

This document provides the first batch of official or authoritative knowledge sources for GW2Radar.

The goal is not to scrape or copy full pages. The correct workflow is:

```text
manual download / manual save
→ record source_url
→ summarize
→ create SourceRegistry entry
→ create KnowledgeArticle
→ link to Entity / Relation / Action / Rule
→ review
→ publish into KB and reports
```

GW2Radar should prioritize:

```text
1. Official ArenaNet / GuildWars2.com sources
2. Official Guild Wars 2 Wiki API documentation
3. Official API endpoint documentation
4. Wiki copyright and licensing references
5. High-value build / guide / competitor references
6. Community sources only as low-confidence trend inputs
```

---

## 1. Collection Rules

### 1.1 Allowed

```text
1. Save source URL.
2. Save page title.
3. Save short summary.
4. Save structured metadata.
5. Save license and usage notes.
6. Save last reviewed date.
7. Link to graph entities and actions.
8. Store small excerpts only when necessary and compliant.
```

### 1.2 Not Allowed

```text
1. Do not mass-copy third-party full pages.
2. Do not mirror third-party websites.
3. Do not scrape aggressively.
4. Do not bypass robots or access restrictions.
5. Do not collect private Discord or private community content without authorization.
6. Do not add player API keys or private account data.
7. Do not add raw private account payloads to the Knowledge Base.
8. Do not present community opinion as official fact.
```

---

## 2. Recommended SourceRegistry Schema

Each source should be recorded using this structure:

```yaml
SourceRegistry:
  source_id: string
  name: string
  source_type: official_api | official_wiki | official_forum | official_policy | public_build_site | competitor_tool | license_reference | community
  source_url: string
  allowed_use: api_json | summary_and_reference | manual_note | metadata_only
  crawl_policy: manual_only | api_only | manual_or_low_frequency | gateway_managed
  default_confidence: float
  license_note: string
  recommended_kb_domain: official | game_system | legendary | returner | build | market | guild | creator | source_registry
```

---

# 3. Level 0 — Official ArenaNet / GuildWars2.com Sources

These should be treated as the highest-priority official sources.

| Source ID | Name | URL | Use in GW2Radar | Recommended File |
|---|---|---|---|---|
| `source:official:guildwars2_home` | Guild Wars 2 Official Website | https://www.guildwars2.com/ | Official news, expansion information, product context | `docs/knowledge_base/official/official_news_sources.md` |
| `source:official:game_update_notes` | Official Forum — Game Update Notes | https://en-forum.guildwars2.com/forum/6-game-update-notes/ | Patch Impact Radar, build freshness checks, market impact notes | `docs/knowledge_base/official/patch_note_sources.md` |
| `source:official:arenanet_content_terms` | ArenaNet Content Terms of Use | https://www.arena.net/legal/content-terms-of-use | Constitution, API governance, fan project policy, content boundary | `docs/knowledge_base/official/arenanet_content_terms_summary.md` |
| `source:official:api_key_management` | ArenaNet API Key Management | https://account.arena.net/applications | User API key tutorial and API Key Safety page | `docs/knowledge_base/official/api_key_management_user_guide.md` |

---

# 4. Level 0 — Official Wiki / API Documentation Sources

These sources are the foundation for the Official GW2 API Compatibility Layer.

| Source ID | Name | URL | Use in GW2Radar | Recommended File |
|---|---|---|---|---|
| `source:gw2wiki:api_main` | Guild Wars 2 API Main | https://wiki.guildwars2.com/wiki/API:Main | API overview, API version context | `docs/knowledge_base/official/gw2_api_summary.md` |
| `source:gw2wiki:api_v2` | API v2 | https://wiki.guildwars2.com/wiki/API:2 | Official API v2 resource model, batching behavior, endpoint structure | `docs/knowledge_base/official/api_v2_resource_model.md` |
| `source:gw2wiki:api_best_practices` | API Best Practices | https://wiki.guildwars2.com/wiki/API:Best_practices | Rate limit, 429 handling, token bucket guidance | `docs/knowledge_base/official/api_rate_limit.md` |
| `source:gw2wiki:api_key` | API Key | https://wiki.guildwars2.com/wiki/API:API_key | API key permissions, scopes, user safety explanation | `docs/knowledge_base/official/api_scopes.md` |
| `source:gw2wiki:api_tokeninfo` | API tokeninfo | https://wiki.guildwars2.com/wiki/API:2/tokeninfo | Scope validation for user API key | `docs/knowledge_base/official/api_tokeninfo.md` |
| `source:gw2wiki:authenticated_endpoints` | Authenticated Endpoint Category | https://wiki.guildwars2.com/wiki/Category:Authenticated_endpoint | Index of private-account endpoints | `docs/knowledge_base/official/authenticated_endpoints_index.md` |

---

# 5. Official API Endpoint Source List

The following pages should be summarized into endpoint-specific knowledge files.

## 5.1 Private Account State Endpoints

| Source ID | Endpoint | URL | GW2Radar Use | Recommended File |
|---|---|---|---|---|
| `source:gw2api:account` | `/v2/account` | https://wiki.guildwars2.com/wiki/API:2/account | Account identity and account-level state | `docs/knowledge_base/official/api_endpoints/account.md` |
| `source:gw2api:characters` | `/v2/characters` | https://wiki.guildwars2.com/wiki/API:2/characters | Character list, returner diagnosis, build fit | `docs/knowledge_base/official/api_endpoints/characters.md` |
| `source:gw2api:account_wallet` | `/v2/account/wallet` | https://wiki.guildwars2.com/wiki/API:2/account/wallet | Wallet currencies for legendary planning | `docs/knowledge_base/official/api_endpoints/account_wallet.md` |
| `source:gw2api:account_bank` | `/v2/account/bank` | https://wiki.guildwars2.com/wiki/API:2/account/bank | Private bank inventory, material/asset state | `docs/knowledge_base/official/api_endpoints/account_bank.md` |
| `source:gw2api:account_achievements` | `/v2/account/achievements` | https://wiki.guildwars2.com/wiki/API:2/account/achievements | Account achievement progress, legendary route status | `docs/knowledge_base/official/api_endpoints/account_achievements.md` |
| `source:gw2api:character_equipmenttabs` | `/v2/characters/:id/equipmenttabs` | https://wiki.guildwars2.com/wiki/API:2/characters/:id/equipmenttabs | Build Fit and Gear Transition Advisor | `docs/knowledge_base/official/api_endpoints/character_equipmenttabs.md` |

Private endpoint policy:

```text
1. Must require API key.
2. Must validate tokeninfo scopes.
3. Must write only to Private Player State Graph or Personal Intelligence Graph.
4. Must never write raw private data to Public Game Graph.
```

---

## 5.2 Public Game Knowledge Endpoints

| Source ID | Endpoint | URL | GW2Radar Use | Recommended File |
|---|---|---|---|---|
| `source:gw2api:achievements` | `/v2/achievements` | https://wiki.guildwars2.com/wiki/API:2/achievements | Achievement / Collection / Goal Graph | `docs/knowledge_base/official/api_endpoints/achievements.md` |
| `source:gw2api:achievement_categories` | `/v2/achievements/categories` | https://wiki.guildwars2.com/wiki/API:2/achievements/categories | Achievement grouping and route planning | `docs/knowledge_base/official/api_endpoints/achievements_categories.md` |
| `source:gw2api:achievements_daily` | `/v2/achievements/daily` | https://wiki.guildwars2.com/wiki/API:2/achievements/daily | Daily Planner | `docs/knowledge_base/official/api_endpoints/achievements_daily.md` |
| `source:gw2api:recipes` | `/v2/recipes` | https://wiki.guildwars2.com/wiki/API:2/recipes | Recipe Graph, Legendary Planner | `docs/knowledge_base/official/api_endpoints/recipes.md` |
| `source:gw2api:recipes_search` | `/v2/recipes/search` | https://wiki.guildwars2.com/wiki/API:2/recipes/search | Input/output recipe lookup | `docs/knowledge_base/official/api_endpoints/recipes_search.md` |
| `source:gw2api:dailycrafting` | `/v2/dailycrafting` | https://wiki.guildwars2.com/wiki/API:2/dailycrafting | Time-gated crafting detection | `docs/knowledge_base/official/api_endpoints/dailycrafting.md` |
| `source:gw2api:itemstats` | `/v2/itemstats` | https://wiki.guildwars2.com/wiki/API:2/itemstats | Gear stats and Build Fit | `docs/knowledge_base/official/api_endpoints/itemstats.md` |
| `source:gw2api:render_service` | API Render Service | https://wiki.guildwars2.com/wiki/API:Render_service | Icons and UI resources | `docs/knowledge_base/official/api_endpoints/render_service.md` |

Public endpoint policy:

```text
1. No user API key required.
2. Use batch IDs where supported.
3. Use gateway/cache/rate limiter.
4. Write to Public Game Graph only.
5. Preserve sanitized Evidence records.
```

---

## 5.3 Commerce / Market Endpoints

| Source ID | Endpoint | URL | GW2Radar Use | Recommended File |
|---|---|---|---|---|
| `source:gw2api:commerce` | `/v2/commerce` | https://wiki.guildwars2.com/wiki/API:2/commerce | Commerce API overview | `docs/knowledge_base/official/api_endpoints/commerce.md` |
| `source:gw2api:commerce_transactions` | `/v2/commerce/transactions` | https://wiki.guildwars2.com/wiki/API:2/commerce/transactions | Private trading history, later-stage feature only | `docs/knowledge_base/official/api_endpoints/commerce_transactions.md` |
| `source:gw2api:commerce_delivery` | `/v2/commerce/delivery` | https://wiki.guildwars2.com/wiki/API:2/commerce/delivery | Private trading delivery state, later-stage feature only | `docs/knowledge_base/official/api_endpoints/commerce_delivery.md` |

Market endpoint policy:

```text
1. Public price data may support Market Radar.
2. Private trading records are not MVP.
3. No automated trading.
4. No guaranteed-profit language.
5. No high-frequency arbitrage.
```

---

# 6. Wiki Copyright / Licensing Sources

These pages should be summarized to define GW2Radar's Wiki usage policy.

| Source ID | Name | URL | Use | Recommended File |
|---|---|---|---|---|
| `source:gw2wiki:copyrights` | Guild Wars 2 Wiki Copyrights | https://wiki.guildwars2.com/wiki/Guild_Wars_2_Wiki:Copyrights | Wiki contribution license notes | `docs/knowledge_base/source_registry/wiki_license_notes.md` |
| `source:gw2wiki:copyrighted_content` | Guild Wars 2 Wiki Copyrighted Content | https://wiki.guildwars2.com/wiki/Guild_Wars_2_Wiki:Copyrighted_content | ArenaNet/NCSoft content boundary | `docs/knowledge_base/source_registry/wiki_copyrighted_content.md` |
| `source:gw2wiki:about` | Guild Wars 2 Wiki About | https://wiki.guildwars2.com/wiki/Guild_Wars_2_Wiki:About | Wiki reliability and editable nature | `docs/knowledge_base/source_registry/wiki_sources.md` |

Wiki usage policy:

```text
1. Store summaries and links.
2. Do not bulk-copy full pages.
3. Preserve attribution where required.
4. Mark Wiki-derived claims as high but still reviewable.
5. Be careful with ArenaNet/NCSoft copyrighted content embedded in Wiki pages.
```

---

# 7. Build / Guide / Competitor Reference Sources

These sources should be used for metadata, source links, and high-level summaries, not full copying.

| Source ID | Name | URL | Use | Recommended File |
|---|---|---|---|---|
| `source:snowcrows:home` | Snow Crows Home | https://snowcrows.com/ | High-end PvE/Open World/WvW build reference | `docs/knowledge_base/build/snowcrows_reference_policy.md` |
| `source:snowcrows:builds` | Snow Crows Builds | https://snowcrows.com/builds | Raid / PvE build metadata reference | `docs/knowledge_base/build/snowcrows_build_metadata.md` |
| `source:snowcrows:open_world` | Snow Crows Open World Builds | https://snowcrows.com/builds/open-world | Returner and Open World build reference | `docs/knowledge_base/build/snowcrows_open_world_reference.md` |
| `source:snowcrows:wvw` | Snow Crows WvW Builds | https://snowcrows.com/builds/wvw | WvW build reference for future guild/team features | `docs/knowledge_base/build/snowcrows_wvw_reference.md` |
| `source:gw2efficiency:home` | gw2efficiency Home | https://gw2efficiency.com/ | Competitor and account-analysis product reference | `docs/knowledge_base/source_registry/competitor_tools.md` |
| `source:gw2efficiency:faq` | gw2efficiency FAQ | https://gw2efficiency.com/frequently-asked-questions | API key safety and user education reference | `docs/knowledge_base/source_registry/api_key_safety_reference_tools.md` |
| `source:gw2wiki:api_applications` | GW2 API Applications List | https://wiki.guildwars2.com/wiki/API:List_of_applications | Ecosystem and competitor tool reference | `docs/knowledge_base/source_registry/competitor_tools.md` |

Build source policy:

```text
1. Store source name, URL, game mode, profession, role, update date if available.
2. Do not copy complete guides.
3. Do not claim absolute meta authority.
4. Preserve attribution and source URL.
5. Mark source freshness.
6. Manual or low-frequency collection only.
```

---

# 8. Third-Party License References

| Source ID | Name | URL | Use | Recommended File |
|---|---|---|---|---|
| `source:license:cc_by_sa_4` | Creative Commons BY-SA 4.0 | https://creativecommons.org/licenses/by-sa/4.0/deed.en | Attribution and ShareAlike reference | `docs/knowledge_base/source_registry/license_reference.md` |
| `source:license:cc_by_sa_3_spdx` | SPDX CC BY-SA 3.0 | https://spdx.org/licenses/CC-BY-SA-3.0.html | SPDX license reference | `docs/knowledge_base/source_registry/license_reference.md` |
| `source:official:arenanet_content_terms` | ArenaNet Content Terms | https://www.arena.net/legal/content-terms-of-use | Official Fan Project / content boundary | `docs/knowledge_base/source_registry/third_party_content_policy.md` |

---

# 9. Community / Trend Sources

Community sources should be treated as low-confidence signals unless manually reviewed.

| Source ID | Name | URL | Use | Recommended File |
|---|---|---|---|---|
| `source:official_forum:game_update_notes` | Official Forum Game Update Notes | https://en-forum.guildwars2.com/forum/6-game-update-notes/ | Official patch and release notes | `docs/knowledge_base/official/patch_note_sources.md` |
| `source:community:official_forum_general` | Official Forum General Discussion | https://en-forum.guildwars2.com/ | FAQ discovery, player pain points | `docs/knowledge_base/source_registry/community_sources.md` |
| `source:community:reddit_guildwars2` | Reddit r/Guildwars2 | https://www.reddit.com/r/Guildwars2/ | Community questions, returner pain points, creator signals | `docs/knowledge_base/source_registry/community_sources.md` |

Community source policy:

```text
1. Use only for trends, FAQ, and content opportunities.
2. Do not treat community claims as official fact.
3. Mark default confidence as low or medium-low.
4. Preserve source links.
5. Do not collect private Discord content without explicit authorization.
```

---

# 10. First Manual Download / Save List

The first batch should include these sources:

```text
1. Guild Wars 2 API Main
2. API v2
3. API Best Practices
4. API Key
5. API tokeninfo
6. ArenaNet Content Terms
7. Game Update Notes
8. API account
9. API characters
10. API account wallet
11. API account bank
12. API account achievements
13. API achievements
14. API recipes
15. API recipes/search
16. API dailycrafting
17. API commerce
18. GW2 Wiki Copyrights
19. Snow Crows homepage / build pages
20. gw2efficiency homepage / FAQ
```

---

# 11. Recommended Repository Files

Create or update:

```text
docs/knowledge_base/source_registry/
├── official_sources.md
├── gw2_api_sources.md
├── wiki_sources.md
├── wiki_license_notes.md
├── wiki_copyrighted_content.md
├── build_sources.md
├── competitor_tools.md
├── license_reference.md
├── citation_and_attribution_policy.md
└── community_sources.md

docs/knowledge_base/official/
├── gw2_api_summary.md
├── api_v2_resource_model.md
├── api_rate_limit.md
├── api_scopes_and_tokeninfo.md
├── official_patch_sources.md
├── arenanet_content_terms_summary.md
└── api_endpoints/
    ├── account.md
    ├── characters.md
    ├── account_wallet.md
    ├── account_bank.md
    ├── account_achievements.md
    ├── achievements.md
    ├── achievements_categories.md
    ├── achievements_daily.md
    ├── recipes.md
    ├── recipes_search.md
    ├── dailycrafting.md
    ├── commerce.md
    ├── commerce_transactions.md
    ├── commerce_delivery.md
    ├── itemstats.md
    └── render_service.md

docs/knowledge_base/build/
├── build_source_policy.md
├── build_metadata_collection_template.md
├── snowcrows_reference_policy.md
├── snowcrows_build_metadata.md
├── snowcrows_open_world_reference.md
├── snowcrows_wvw_reference.md
└── gw2efficiency_reference_notes.md
```

---

# 12. Manual Source Entry Template

Use this for every source:

```yaml
source_id: source:gw2wiki:api_v2
name: Guild Wars 2 Wiki API:2
source_type: official_wiki
source_url: "https://wiki.guildwars2.com/wiki/API:2"
allowed_use: summary_and_reference
crawl_policy: manual_or_low_frequency
default_confidence: 0.95
license_note: "GW2 Wiki contributor content and ArenaNet/NCSoft content require attribution and copyright handling."
recommended_kb_domain: official
```

---

# 13. KnowledgeArticle Template

Use this for every summarized knowledge page:

```yaml
kb_id: kb:official:api_v2
title: GW2 API v2 Summary
domain: official
content_type: source_note
summary: "GW2 API v2 provides resource-oriented endpoints and supports querying multiple resources."
linked_entities:
  - entity:api:gw2_v2
linked_actions:
  - INGEST_SOURCE
  - VALIDATE_API_SCOPE
confidence: 0.95
review_status: reviewed
source_refs:
  - source:gw2wiki:api_v2
```

---

# 14. Codex Task — Create First Source Registry Batch

```text
Current project: GW2Radar

Task:
Create the first batch of official and authoritative knowledge source registry documents.

Requirements:
1. Do not scrape pages automatically.
2. Do not copy full third-party page content.
3. Create docs/knowledge_base/source_registry/.
4. Create docs/knowledge_base/official/.
5. Add source registry entries for:
   - GW2 API Main
   - GW2 API v2
   - API Best Practices
   - API Key
   - tokeninfo
   - ArenaNet Content Terms
   - Game Update Notes
   - GW2 Wiki Copyrights
   - Snow Crows
   - gw2efficiency
6. For each source, record:
   - source_id
   - name
   - source_type
   - source_url
   - allowed_use
   - crawl_policy
   - default_confidence
   - license_note
   - recommended KB domain
7. Create official API summary markdown files:
   - gw2_api_summary.md
   - api_v2_resource_model.md
   - api_rate_limit.md
   - api_scopes_and_tokeninfo.md
8. Create build source policy markdown:
   - build_source_policy.md
   - snowcrows_reference_policy.md
   - gw2efficiency_reference_notes.md
9. Do not add API keys or private player data.
10. Do not modify runtime code.

Acceptance:
- Source registry files exist.
- Each source has clear allowed_use and license_note.
- No full-page copyrighted content copied.
- No private data added.
- README links to the source registry.
```

---

## 15. Final Principle

First-batch knowledge sources should prioritize:

```text
1. Official API documentation
2. API rate limit and tokeninfo documentation
3. ArenaNet content/API use policy
4. Official patch notes
5. GW2 Wiki copyright and license references
6. Snow Crows and gw2efficiency as reference sources
```

Final rule:

```text
Official sources go into Evidence and Public Game Graph.
Wiki and build websites go into Knowledge Base summaries and source links.
Community sources are low-confidence trend inputs.
Expert rules are the highest-value commercial intelligence assets.
```
