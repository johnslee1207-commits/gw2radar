# Official Source Registry

This registry records official and authoritative GW2 sources for manual collection, evidence registration, Knowledge Base summaries, and later graph linking.

Policy:

- Store source metadata, short summaries, and links.
- Do not mirror full pages or bulk-copy third-party content.
- Do not store credentials, secrets, raw account payloads, or private player data.
- Use downloaded PDFs and `data/kb/pdf_evidence.jsonl` as local evidence artifacts when available.

## Level 0 Official Sources

| Source ID | Name | Source Type | URL | Allowed Use | Crawl Policy | Confidence | Recommended KB File | Coverage |
|---|---|---|---|---|---|---:|---|---|
| `source:official:guildwars2_home` | Guild Wars 2 Official Website | official_news | https://www.guildwars2.com/ | summary_and_reference | manual_only | 0.95 | `docs/knowledge_base/official/official_news_sources.md` | implemented |
| `source:official:game_update_notes` | Official Forum Game Update Notes | official_news | https://en-forum.guildwars2.com/forum/6-game-update-notes/ | summary_and_reference | manual_only | 0.95 | `docs/knowledge_base/official/patch_note_sources.md` | implemented: source note plus 182 PDF artifacts inventoried |
| `source:official:arenanet_content_terms` | ArenaNet Content Terms of Use | official_policy | https://www.arena.net/legal/content-terms-of-use | summary_and_reference | manual_only | 0.9 | `docs/knowledge_base/official/arenanet_content_terms_summary.md` | partial |
| `source:official:credential_management` | ArenaNet Application Management | official_policy | https://account.arena.net/applications | manual_note | manual_only | 0.9 | `docs/knowledge_base/official/api_credential_management_user_guide.md` | missing |

## Official Wiki / API Documentation

| Source ID | Name | Source Type | URL | Allowed Use | Crawl Policy | Confidence | Recommended KB File | Coverage |
|---|---|---|---|---|---|---:|---|---|
| `source:gw2wiki:api_main` | Guild Wars 2 API Main | official_wiki | https://wiki.guildwars2.com/wiki/API:Main | summary_and_reference | manual_or_low_frequency | 0.95 | `docs/knowledge_base/official/gw2_api_summary.md` | implemented |
| `source:gw2wiki:api_v2` | API v2 | official_wiki | https://wiki.guildwars2.com/wiki/API:2 | summary_and_reference | manual_or_low_frequency | 0.95 | `docs/knowledge_base/official/api_v2_resource_model.md` | implemented |
| `source:gw2wiki:api_best_practices` | API Best Practices | official_wiki | https://wiki.guildwars2.com/wiki/API:Best_practices | summary_and_reference | manual_or_low_frequency | 0.95 | `docs/knowledge_base/official/api_rate_limit.md` | implemented |
| `source:gw2wiki:api_key` | API credential page | official_wiki | https://wiki.guildwars2.com/wiki/API:API_key | summary_and_reference | manual_or_low_frequency | 0.95 | `docs/knowledge_base/official/api_scopes_and_tokeninfo.md` | partial |
| `source:gw2wiki:api_tokeninfo` | API tokeninfo | official_wiki | https://wiki.guildwars2.com/wiki/API:2/tokeninfo | summary_and_reference | manual_or_low_frequency | 0.95 | `docs/knowledge_base/official/api_scopes_and_tokeninfo.md` | implemented |
| `source:gw2wiki:authenticated_endpoints` | Authenticated Endpoint Category | official_wiki | https://wiki.guildwars2.com/wiki/Category:Authenticated_endpoint | summary_and_reference | manual_or_low_frequency | 0.9 | `docs/knowledge_base/official/authenticated_endpoints_index.md` | implemented |

## Endpoint Source Coverage

| Source ID | Endpoint | URL | Graph Layer | Recommended File | Coverage |
|---|---|---|---|---|---|
| `source:gw2api:account` | `/v2/account` | https://wiki.guildwars2.com/wiki/API:2/account | private_player_state | `docs/knowledge_base/official/api_endpoints/account.md` | implemented |
| `source:gw2api:characters` | `/v2/characters` | https://wiki.guildwars2.com/wiki/API:2/characters | private_player_state | `docs/knowledge_base/official/api_endpoints/characters.md` | implemented |
| `source:gw2api:account_wallet` | `/v2/account/wallet` | https://wiki.guildwars2.com/wiki/API:2/account/wallet | private_player_state | `docs/knowledge_base/official/api_endpoints/account_wallet.md` | implemented |
| `source:gw2api:account_bank` | `/v2/account/bank` | https://wiki.guildwars2.com/wiki/API:2/account/bank | private_player_state | `docs/knowledge_base/official/api_endpoints/account_bank.md` | implemented |
| `source:gw2api:account_achievements` | `/v2/account/achievements` | https://wiki.guildwars2.com/wiki/API:2/account/achievements | private_player_state | `docs/knowledge_base/official/api_endpoints/account_achievements.md` | implemented |
| `source:gw2api:character_equipmenttabs` | `/v2/characters/:id/equipmenttabs` | https://wiki.guildwars2.com/wiki/API:2/characters/:id/equipmenttabs | private_player_state | `docs/knowledge_base/official/api_endpoints/character_equipmenttabs.md` | implemented |
| `source:gw2api:achievements` | `/v2/achievements` | https://wiki.guildwars2.com/wiki/API:2/achievements | public_game_data | `docs/knowledge_base/official/api_endpoints/achievements.md` | implemented |
| `source:gw2api:achievement_categories` | `/v2/achievements/categories` | https://wiki.guildwars2.com/wiki/API:2/achievements/categories | public_game_data | `docs/knowledge_base/official/api_endpoints/achievements_categories.md` | implemented |
| `source:gw2api:achievements_daily` | `/v2/achievements/daily` | https://wiki.guildwars2.com/wiki/API:2/achievements/daily | public_game_data | `docs/knowledge_base/official/api_endpoints/achievements_daily.md` | implemented |
| `source:gw2api:recipes` | `/v2/recipes` | https://wiki.guildwars2.com/wiki/API:2/recipes | public_game_data | `docs/knowledge_base/official/api_endpoints/recipes.md` | implemented |
| `source:gw2api:recipes_search` | `/v2/recipes/search` | https://wiki.guildwars2.com/wiki/API:2/recipes/search | public_game_data | `docs/knowledge_base/official/api_endpoints/recipes_search.md` | implemented |
| `source:gw2api:dailycrafting` | `/v2/dailycrafting` | https://wiki.guildwars2.com/wiki/API:2/dailycrafting | public_game_data | `docs/knowledge_base/official/api_endpoints/dailycrafting.md` | implemented |
| `source:gw2api:itemstats` | `/v2/itemstats` | https://wiki.guildwars2.com/wiki/API:2/itemstats | public_game_data | `docs/knowledge_base/official/api_endpoints/itemstats.md` | implemented |
| `source:gw2api:render_service` | API Render Service | https://wiki.guildwars2.com/wiki/API:Render_service | public_game_data | `docs/knowledge_base/official/api_endpoints/render_service.md` | implemented |
| `source:gw2api:commerce` | `/v2/commerce` | https://wiki.guildwars2.com/wiki/API:2/commerce | market_public_data | `docs/knowledge_base/official/api_endpoints/commerce.md` | implemented |
| `source:gw2api:commerce_transactions` | `/v2/commerce/transactions` | https://wiki.guildwars2.com/wiki/API:2/commerce/transactions | private_player_state | `docs/knowledge_base/official/api_endpoints/commerce_transactions.md` | implemented |
| `source:gw2api:commerce_delivery` | `/v2/commerce/delivery` | https://wiki.guildwars2.com/wiki/API:2/commerce/delivery | private_player_state | `docs/knowledge_base/official/api_endpoints/commerce_delivery.md` | implemented |
