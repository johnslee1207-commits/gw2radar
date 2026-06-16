# Knowledge Source Coverage Analysis

Date: 2026-06-17

Basis:

- `docs/analysis/GW2Radar_Knowledge_Source_Registry_Official_Authoritative_Links.md`
- `data/kb/pdf_inventory.csv`
- `data/kb/pdf_evidence.jsonl`
- existing `docs/knowledge_base/**.md`

## Executive Summary

Current Knowledge Base source implementation is strongest for official GW2 API PDFs and endpoint summaries. It is weaker for source registry governance, wiki license policy, build/guide source attribution, competitor references, and community trend-source policy.

Overall maturity:

| Area | Current Coverage | Maturity |
|---|---:|---|
| Downloaded PDF inventory and evidence | 216/216 PDFs | high |
| Tier 0 official API summaries | 6 core files | medium-high |
| Tier 1 endpoint summaries | 17 implemented / 17 requested | high |
| Recent patch note inventory | 45 P2 patch PDFs inventoried | medium |
| Patch note structured summaries | 0 generated | low |
| Source registry documents | 6 registry files plus official coverage analysis | medium-high |
| Wiki license/copyright policy summaries | registry only | low |
| Build / guide source policy | registry only plus `build_fit_rules.md` | low |
| Competitor and ecosystem references | registry only | low |
| Community trend source policy | registry only | low |

## Implemented Source Assets

Local source artifacts:

| Category | Count | Notes |
|---|---:|---|
| official_api | 2 | API main and API v2 PDFs |
| official_api_endpoint | 12 | Core account, achievement, recipe, daily crafting, commerce endpoint PDFs |
| api_governance | 1 | Best practices PDF |
| api_permission | 1 | tokeninfo PDF |
| api_key | 1 | credential-related source PDF, kept out of KB text as sensitive wording |
| arenanet_policy | 6 | ArenaNet policy PDFs |
| patch_note | 182 | 2024/2025/2026 plus archive patch PDFs |
| wiki_meta | 8 | Wiki help/community/meta PDFs |
| low_priority | 3 | Talk pages and unrelated item page |

Generated indexes:

- `data/kb/pdf_inventory.csv`
- `data/kb/pdf_evidence.jsonl`

Generated KB summaries:

- `docs/knowledge_base/official/gw2_api_summary.md`
- `docs/knowledge_base/official/api_v2_resource_model.md`
- `docs/knowledge_base/official/api_rate_limit.md`
- `docs/knowledge_base/official/api_scopes_and_tokeninfo.md`
- `docs/knowledge_base/official/api_key_safety.md`
- `docs/knowledge_base/official/arenanet_content_terms_summary.md`
- `docs/knowledge_base/official/api_endpoints/*.md`

## Source Gaps To Fill

### P0 — Official Trust And Source Registry Completion

These sources directly support API governance, privacy, and source attribution.

| Needed File | Source ID | Reference Link | Why It Matters |
|---|---|---|---|
| `docs/knowledge_base/official/official_news_sources.md` | `source:official:guildwars2_home` | https://www.guildwars2.com/ | implemented |
| `docs/knowledge_base/official/patch_note_sources.md` | `source:official:game_update_notes` | https://en-forum.guildwars2.com/forum/6-game-update-notes/ | implemented |
| `docs/knowledge_base/official/authenticated_endpoints_index.md` | `source:gw2wiki:authenticated_endpoints` | https://wiki.guildwars2.com/wiki/Category:Authenticated_endpoint | implemented |
| `docs/knowledge_base/source_registry/citation_and_attribution_policy.md` | multiple | https://wiki.guildwars2.com/wiki/Guild_Wars_2_Wiki:Copyrights | Attribution policy before broad KB publication |
| `docs/knowledge_base/source_registry/third_party_content_policy.md` | `source:official:arenanet_content_terms` | https://www.arena.net/legal/content-terms-of-use | Fan/content-use boundary |

### P1 — Missing Endpoint Summaries

These complete the endpoint list from the authoritative source plan.

| Needed File | Source ID | Reference Link | Graph Layer |
|---|---|---|---|
| `docs/knowledge_base/official/api_endpoints/character_equipmenttabs.md` | `source:gw2api:character_equipmenttabs` | https://wiki.guildwars2.com/wiki/API:2/characters/:id/equipmenttabs | implemented |
| `docs/knowledge_base/official/api_endpoints/itemstats.md` | `source:gw2api:itemstats` | https://wiki.guildwars2.com/wiki/API:2/itemstats | implemented |
| `docs/knowledge_base/official/api_endpoints/render_service.md` | `source:gw2api:render_service` | https://wiki.guildwars2.com/wiki/API:Render_service | implemented |
| `docs/knowledge_base/official/api_endpoints/commerce_transactions.md` | `source:gw2api:commerce_transactions` | https://wiki.guildwars2.com/wiki/API:2/commerce/transactions | implemented |
| `docs/knowledge_base/official/api_endpoints/commerce_delivery.md` | `source:gw2api:commerce_delivery` | https://wiki.guildwars2.com/wiki/API:2/commerce/delivery | implemented |

### P2 — Wiki License And Copyright Handling

These are needed before wiki-derived summaries move from draft to reviewed.

| Needed File | Source ID | Reference Link | Recommended Use |
|---|---|---|---|
| `docs/knowledge_base/source_registry/wiki_license_notes.md` | `source:gw2wiki:copyrights` | https://wiki.guildwars2.com/wiki/Guild_Wars_2_Wiki:Copyrights | Attribution and license notes |
| `docs/knowledge_base/source_registry/wiki_copyrighted_content.md` | `source:gw2wiki:copyrighted_content` | https://wiki.guildwars2.com/wiki/Guild_Wars_2_Wiki:Copyrighted_content | ArenaNet/NCSoft content boundary |
| `docs/knowledge_base/source_registry/wiki_sources.md` | `source:gw2wiki:about` | https://wiki.guildwars2.com/wiki/Guild_Wars_2_Wiki:About | Wiki reliability and editable-source note |

### P3 — Build / Guide Source Policy

These support Build Fit, Guild Readiness, and Creator Intelligence without copying third-party guide content.

| Needed File | Source ID | Reference Link | Recommended Use |
|---|---|---|---|
| `docs/knowledge_base/build/build_source_policy.md` | internal policy | `docs/knowledge_base/source_registry/build_sources.md` | Build source collection rules |
| `docs/knowledge_base/build/build_metadata_collection_template.md` | internal template | `docs/knowledge_base/source_registry/build_sources.md` | Metadata-only build capture |
| `docs/knowledge_base/build/snowcrows_reference_policy.md` | `source:snowcrows:home` | https://snowcrows.com/ | Attribution and freshness policy |
| `docs/knowledge_base/build/snowcrows_build_metadata.md` | `source:snowcrows:builds` | https://snowcrows.com/builds | Build metadata reference |
| `docs/knowledge_base/build/snowcrows_open_world_reference.md` | `source:snowcrows:open_world` | https://snowcrows.com/builds/open-world | Returner/open-world build reference |
| `docs/knowledge_base/build/snowcrows_wvw_reference.md` | `source:snowcrows:wvw` | https://snowcrows.com/builds/wvw | Future guild/team readiness |

### P4 — Competitor And Community Intelligence Sources

These support product positioning, trust-page wording, and creator intelligence. They should not drive official fact rules.

| Needed File | Source ID | Reference Link | Recommended Use |
|---|---|---|---|
| `docs/knowledge_base/source_registry/api_credential_safety_reference_tools.md` | `source:gw2efficiency:faq` | https://gw2efficiency.com/frequently-asked-questions | User education reference |
| `docs/knowledge_base/source_registry/competitor_tools.md` | `source:gw2efficiency:home` | https://gw2efficiency.com/ | Product comparison and feature-gap analysis |
| `docs/knowledge_base/source_registry/competitor_tools.md` | `source:gw2wiki:api_applications` | https://wiki.guildwars2.com/wiki/API:List_of_applications | Public ecosystem overview |
| `docs/knowledge_base/source_registry/community_sources.md` | `source:community:official_forum_general` | https://en-forum.guildwars2.com/ | FAQ and pain-point discovery |
| `docs/knowledge_base/source_registry/community_sources.md` | `source:community:reddit_guildwars2` | https://www.reddit.com/r/Guildwars2/ | Low-confidence community trends |

## Recommended Next Work

1. Generate patch-note structured summaries for 2026/2025/2024 only.
2. Add wiki/license policy summaries before marking wiki-derived KB as reviewed.
3. Add build-source metadata templates and Snow Crows attribution policy.
4. Add source freshness and attribution fields to report quality scoring.
5. Promote reviewed official source notes into persisted KnowledgeArticle records.

## Governance Boundary

- Links are source references, not permission to copy full text.
- Community sources remain low-confidence trend inputs.
- Private account endpoints must remain in private graph layers.
- Draft KB articles must not drive high-priority recommendations.
