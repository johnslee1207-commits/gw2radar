# Build And Guide Source Registry

This registry defines high-value build and guide sources for Build Fit, Returner, Guild, and Creator intelligence.

Policy:

- Store source name, URL, game mode, profession, role, and freshness metadata.
- Do not copy full guides, rotations, or full page text.
- Do not claim any third-party build site is absolute meta authority.
- Mark build-source facts as reviewable and freshness-sensitive.

| Source ID | Name | URL | Allowed Use | Crawl Policy | Confidence | Recommended File | Coverage |
|---|---|---|---|---|---:|---|---|
| `source:snowcrows:home` | Snow Crows Home | https://snowcrows.com/ | summary_and_reference | manual_or_low_frequency | 0.75 | `docs/knowledge_base/build/snowcrows_reference_policy.md` | missing |
| `source:snowcrows:builds` | Snow Crows Builds | https://snowcrows.com/builds | metadata_only | manual_or_low_frequency | 0.75 | `docs/knowledge_base/build/snowcrows_build_metadata.md` | missing |
| `source:snowcrows:open_world` | Snow Crows Open World Builds | https://snowcrows.com/builds/open-world | metadata_only | manual_or_low_frequency | 0.7 | `docs/knowledge_base/build/snowcrows_open_world_reference.md` | missing |
| `source:snowcrows:wvw` | Snow Crows WvW Builds | https://snowcrows.com/builds/wvw | metadata_only | manual_or_low_frequency | 0.7 | `docs/knowledge_base/build/snowcrows_wvw_reference.md` | missing |

## Needed Additions

1. Create `build_source_policy.md`.
2. Create `build_metadata_collection_template.md`.
3. Create Snow Crows reference policy files without copying guide bodies.
4. Connect build source freshness to Build Fit and Creator Intelligence quality scoring.
