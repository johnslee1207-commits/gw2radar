---
title: PDF source processing report
domain: official
content_type: source_note
summary: Processing report for locally downloaded GW2 source PDFs, including classification, evidence indexing, and no-full-text-copy boundaries.
source_refs:
linked_entities: gw2:system:official_api
linked_actions: INGEST_SOURCE
confidence: 0.8
review_status: draft
---

# PDF Source Processing Report

## Scope

Processed the locally downloaded PDF source artifacts under:

```text
docs/knowledge_base/official
```

The PDFs were treated as source artifacts, not as final Knowledge Base articles.

## Results

- PDF source artifacts processed: 216
- Total PDF size: 92,761,034 bytes
- Inventory records generated: 216
- Evidence records generated: 216
- Tier 0 / Tier 1 extracted text files: 23
- Initial KnowledgeArticle markdown summaries: 18

## Source Organization

PDFs were moved into:

```text
docs/knowledge_base/_sources/pdf/
```

Category distribution:

```text
api_governance: 1
api_key: 1
api_permission: 1
arenanet_policy: 6
low_priority: 3
official_api: 2
official_api_endpoint: 12
patch_note: 182
wiki_meta: 8
```

Priority distribution:

```text
P0: 11
P1: 12
P2: 45
P3: 145
P4: 3
```

## Generated Indexes

```text
data/kb/pdf_inventory.csv
data/kb/pdf_evidence.jsonl
```

Full extracted PDF text is intermediate processing data and is ignored by Git:

```text
data/extracted/pdf_text/
```

## Generated KB Summaries

Tier 0 summaries:

```text
docs/knowledge_base/official/gw2_api_summary.md
docs/knowledge_base/official/api_v2_resource_model.md
docs/knowledge_base/official/api_rate_limit.md
docs/knowledge_base/official/api_scopes_and_tokeninfo.md
docs/knowledge_base/official/api_key_safety.md
docs/knowledge_base/official/arenanet_content_terms_summary.md
```

Tier 1 endpoint summaries:

```text
docs/knowledge_base/official/api_endpoints/*.md
```

## Governance Notes

- No web scraping or downloading was performed.
- Source PDFs were preserved as evidence artifacts.
- Extracted full text is not committed.
- KB markdown summaries intentionally avoid full-text copying.
- Generated summaries are marked `review_status: draft` until reviewed.
- Patch notes were inventoried and grouped, but not converted into final KnowledgeArticle summaries in this stage.
