# Community Source Registry

Community sources are useful for trend discovery, FAQ gaps, returner pain points, and creator opportunities. They are not official fact sources.

Policy:

- Use only public sources.
- Do not collect private Discord, private guild, or private community content without explicit authorization.
- Store short summaries and links only.
- Mark default confidence low or medium-low unless manually reviewed.

| Source ID | Name | URL | Allowed Use | Crawl Policy | Confidence | Recommended File | Coverage |
|---|---|---|---|---|---:|---|---|
| `source:official_forum:game_update_notes` | Official Forum Game Update Notes | https://en-forum.guildwars2.com/forum/6-game-update-notes/ | summary_and_reference | manual_only | 0.95 | `docs/knowledge_base/official/patch_note_sources.md` | partial |
| `source:community:official_forum_general` | Official Forum General Discussion | https://en-forum.guildwars2.com/ | manual_note | manual_only | 0.45 | `docs/knowledge_base/source_registry/community_sources.md` | this file |
| `source:community:reddit_guildwars2` | Reddit r/Guildwars2 | https://www.reddit.com/r/Guildwars2/ | manual_note | manual_only | 0.35 | `docs/knowledge_base/source_registry/community_sources.md` | this file |

## Needed Additions

1. Add community signal review checklist for creator intelligence.
2. Add topic freshness and confidence scoring for public discussion summaries.
3. Keep community-derived claims out of official KB and high-priority rules.
