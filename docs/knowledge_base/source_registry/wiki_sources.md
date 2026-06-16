# Wiki Source Registry

This registry defines how GW2Radar may use Guild Wars 2 Wiki pages.

Policy:

- Use source links, metadata, summaries, and attribution notes.
- Do not mirror full wiki pages.
- Treat wiki facts as high-confidence but still reviewable.
- Keep ArenaNet/NCSoft copyrighted media and game text boundaries explicit.

| Source ID | Name | URL | Allowed Use | Crawl Policy | Confidence | Recommended File | Coverage |
|---|---|---|---|---|---:|---|---|
| `source:gw2wiki:copyrights` | Guild Wars 2 Wiki Copyrights | https://wiki.guildwars2.com/wiki/Guild_Wars_2_Wiki:Copyrights | summary_and_reference | manual_only | 0.8 | `docs/knowledge_base/source_registry/wiki_license_notes.md` | missing |
| `source:gw2wiki:copyrighted_content` | Guild Wars 2 Wiki Copyrighted Content | https://wiki.guildwars2.com/wiki/Guild_Wars_2_Wiki:Copyrighted_content | summary_and_reference | manual_only | 0.8 | `docs/knowledge_base/source_registry/wiki_copyrighted_content.md` | missing |
| `source:gw2wiki:about` | Guild Wars 2 Wiki About | https://wiki.guildwars2.com/wiki/Guild_Wars_2_Wiki:About | summary_and_reference | manual_only | 0.75 | `docs/knowledge_base/source_registry/wiki_sources.md` | this file |
| `source:gw2wiki:community_portal` | Guild Wars 2 Wiki Community Portal | https://wiki.guildwars2.com/wiki/Guild_Wars_2_Wiki:Community_portal | metadata_only | manual_only | 0.6 | `docs/knowledge_base/source_registry/wiki_sources.md` | PDF artifact inventoried |
| `source:gw2wiki:help_editing` | Guild Wars 2 Wiki Help Editing | https://wiki.guildwars2.com/wiki/Help:Editing | metadata_only | manual_only | 0.6 | `docs/knowledge_base/source_registry/wiki_sources.md` | PDF artifact inventoried |

## Needed Additions

1. Create `wiki_license_notes.md` with attribution and ShareAlike handling notes.
2. Create `wiki_copyrighted_content.md` with ArenaNet/NCSoft content-boundary notes.
3. Link wiki-derived KB articles to the relevant source ID instead of only local PDF evidence.
