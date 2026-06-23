# GW2Radar Downloaded PDF Knowledge Source Processing Plan

```text
Document ID: GW2RADAR_DOWNLOADED_PDF_KNOWLEDGE_SOURCE_PROCESSING_PLAN
Project: GW2Radar
Version: v0.1
Status: Codex-ready Processing Plan
Input Baseline:
  pdflist.txt
  Local source directory:
    D:\Projects\gw2radar\docs\knowledge_base\official
Observed Inventory:
  216 PDF files
  Total size: approximately 92.8 MB
Primary Goal:
  Convert downloaded PDF source artifacts into evidence-backed,
  summarized, graph-linked Knowledge Base assets without copying full text.
```

---

## 0. Purpose

This document defines how to process the downloaded GW2Radar PDF source files.

The current downloaded PDF set includes:

```text
1. GW2 API documentation PDFs.
2. GW2 API endpoint PDFs.
3. ArenaNet account / API key / security / game content PDFs.
4. Game Update Notes PDFs from 2017–2026.
5. Guild Wars 2 Wiki meta/help/community PDFs.
6. Some low-priority or unrelated PDFs.
```

The purpose is **not** to directly dump all PDF text into the Knowledge Base.

The correct workflow is:

```text
PDF source artifact
→ PDF inventory
→ PDF classification
→ text extraction for selected tiers
→ evidence record
→ KnowledgeArticle summary
→ entity/action linking
→ review
→ publish into Knowledge Base / Graph / Reports
```

---

## 1. Current PDF Asset Assessment

### 1.1 Source Location

Current local source directory from the uploaded file list:

```text
D:\Projects\gw2radar\docs\knowledge_base\official
```

### 1.2 Inventory Scale

The uploaded `pdflist.txt` shows:

```text
216 PDF files
92,761,034 bytes
```

These PDFs should be treated as **source artifacts**, not directly as final Knowledge Base articles.

---

## 2. PDF Content Categories

The current file list can be divided into five major categories.

---

## 2.1 Category A — API / Official Documentation

Examples:

```text
API_Main - Guild Wars 2 Wiki (GW2W).pdf
API_2 - Guild Wars 2 Wiki (GW2W).pdf
API_2_tokeninfo - Guild Wars 2 Wiki (GW2W).pdf
API_API key - Guild Wars 2 Wiki (GW2W).pdf
API_Best practices - Guild Wars 2 Wiki (GW2W).pdf
API_2_account - Guild Wars 2 Wiki (GW2W).pdf
API_2_characters - Guild Wars 2 Wiki (GW2W).pdf
API_2_account_wallet - Guild Wars 2 Wiki (GW2W).pdf
API_2_account_bank - Guild Wars 2 Wiki (GW2W).pdf
API_2_account_achievements - Guild Wars 2 Wiki (GW2W).pdf
API_2_achievements - Guild Wars 2 Wiki (GW2W).pdf
API_2_recipes - Guild Wars 2 Wiki (GW2W).pdf
API_2_recipes_search - Guild Wars 2 Wiki (GW2W).pdf
API_2_commerce - Guild Wars 2 Wiki (GW2W).pdf
API_2_dailycrafting - Guild Wars 2 Wiki (GW2W).pdf
```

### Use

These are **highest-priority documents**.

They support:

```text
OfficialGw2ApiClient
Gw2ApiGateway
PermissionValidator
EndpointSchema
EvidenceWriter
Public Game Graph
Private Player State Graph
```

### Processing Priority

```text
Tier 0 / Tier 1
```

---

## 2.2 Category B — ArenaNet Account / Security / Policy Documents

Examples:

```text
ArenaNet.pdf
ArenaNet-apikey.pdf
ArenaNet-game content.pdf
ArenaNet-overview.pdf
ArenaNet-security.pdf
ArenaNet-setting.pdf
```

### Use

These support:

```text
GW2Radar Project Constitution
API Key Safety
Production Security Upgrade
User privacy documentation
Content/API usage policy
```

### Processing Priority

```text
Tier 0
```

---

## 2.3 Category C — Game Update Notes

Examples from the current list:

```text
Game Update Notes_ June 2, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf
Game Update Notes_ May 12, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf
Game Update Notes_ April 14, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf
Game Update Notes_ March 31, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf
Game Update Notes_ February 24, 2026 - Game Update Notes - Guild Wars 2 Forums.pdf
Game Update Notes_ December 9, 2025 - Game Update Notes - Guild Wars 2 Forums.pdf
Game Update Notes_ August 19, 2025 - Game Update Notes - Guild Wars 2 Forums.pdf
Game Update Notes_ June 24, 2025 - Game Update Notes - Guild Wars 2 Forums.pdf
...
```

### Use

These support:

```text
Patch Impact Radar
Build Freshness Checker
Market Impact Signal
Profession / Skill / Trait Change Tracking
Creator Intelligence
```

### Processing Priority

```text
Tier 2 for 2026 / 2025 / 2024
Tier 3 or archive for 2017–2023
```

### Important Rule

Patch notes should not be copied wholesale into KB.

Instead, extract structured summaries:

```yaml
patch_id: patch:2026-06-02
date: 2026-06-02
source_pdf: ...
summary: ...
changed_professions: []
changed_skills: []
changed_traits: []
changed_items: []
changed_rewards: []
affected_systems: []
possible_build_impact: []
possible_market_impact: []
confidence: 0.85
review_status: draft
```

---

## 2.4 Category D — Wiki Meta / Help / Community Pages

Examples:

```text
Guild Wars 2 Wiki.pdf
Guild Wars 2 Wiki_Community portal - Guild Wars 2 Wiki (GW2W).pdf
Guild Wars 2 Wiki_Admin noticeboard - Guild Wars 2 Wiki (GW2W).pdf
Help_Contents - Guild Wars 2 Wiki (GW2W).pdf
Help_Editing - Guild Wars 2 Wiki (GW2W).pdf
Recent changes - Guild Wars 2 Wiki (GW2W).pdf
Quick access links - Guild Wars 2 Wiki (GW2W).pdf
```

### Use

These are not core game knowledge. They are useful for:

```text
Wiki source policy
Wiki editability note
Wiki reliability note
Source registry documentation
```

### Processing Priority

```text
Tier 3
```

---

## 2.5 Category E — Low Priority / Archive

Examples:

```text
Gallant Longbow Skin - Guild Wars 2 Wiki (GW2W).pdf
API talk_2 - Guild Wars 2 Wiki (GW2W).pdf
Editing API talk_2 - Guild Wars 2 Wiki (GW2W).pdf
```

### Use

No immediate use for MVP or commercial intelligence.

### Processing Priority

```text
Tier 4 — archive or ignore for now
```

---

# 3. Tier-Based Processing Strategy

## 3.1 Tier 0 — Immediate Processing

Tier 0 supports constitution, API governance, security, and API compatibility.

Process first:

```text
API_Main
API_2
API_Best practices
API_API key
API_2_tokeninfo
ArenaNet-apikey
ArenaNet-security
ArenaNet-game content
ArenaNet-overview
```

Expected outputs:

```text
docs/knowledge_base/official/gw2_api_summary.md
docs/knowledge_base/official/api_v2_resource_model.md
docs/knowledge_base/official/api_rate_limit.md
docs/knowledge_base/official/api_scopes_and_tokeninfo.md
docs/knowledge_base/official/api_key_safety.md
docs/knowledge_base/official/arenanet_content_terms_summary.md
```

---

## 3.2 Tier 1 — API Endpoint Implementation Documents

Tier 1 supports P1/P2/P3 engineering implementation.

Process second:

```text
API_2_account
API_2_characters
API_2_account_wallet
API_2_account_bank
API_2_account_achievements
API_2_achievements
API_2_achievements_categories
API_2_achievements_daily
API_2_recipes
API_2_recipes_search
API_2_dailycrafting
API_2_commerce
```

Expected outputs:

```text
docs/knowledge_base/official/api_endpoints/account.md
docs/knowledge_base/official/api_endpoints/characters.md
docs/knowledge_base/official/api_endpoints/account_wallet.md
docs/knowledge_base/official/api_endpoints/account_bank.md
docs/knowledge_base/official/api_endpoints/account_achievements.md
docs/knowledge_base/official/api_endpoints/achievements.md
docs/knowledge_base/official/api_endpoints/achievements_categories.md
docs/knowledge_base/official/api_endpoints/achievements_daily.md
docs/knowledge_base/official/api_endpoints/recipes.md
docs/knowledge_base/official/api_endpoints/recipes_search.md
docs/knowledge_base/official/api_endpoints/dailycrafting.md
docs/knowledge_base/official/api_endpoints/commerce.md
```

Each endpoint summary should include:

```yaml
endpoint:
method:
requires_api_key:
required_scopes:
public_or_private_graph_layer:
cache_ttl:
batch_supported:
primary_entities:
primary_actions:
error_handling_notes:
source_pdf:
evidence_id:
```

---

## 3.3 Tier 2 — Recent Patch Notes

Tier 2 supports Patch Impact Radar and Build Freshness.

Process only recent years first:

```text
2026
2025
2024
```

Top 2026 examples:

```text
Game Update Notes_ June 2, 2026
Game Update Notes_ May 12, 2026
Game Update Notes_ April 14, 2026
Game Update Notes_ March 31, 2026
Game Update Notes_ March 17, 2026
Game Update Notes_ February 24, 2026
Game Update Notes_ February 3, 2026
Game Update Notes_ January 13, 2026
```

Expected outputs:

```text
docs/knowledge_base/patch_notes/2026/2026-06-02.md
docs/knowledge_base/patch_notes/2026/2026-05-12.md
docs/knowledge_base/patch_notes/2026/2026-04-14.md
...
```

Patch note summary schema:

```yaml
patch_id:
date:
source_pdf:
summary:
changed_professions:
changed_skills:
changed_traits:
changed_items:
changed_rewards:
affected_systems:
possible_build_impact:
possible_market_impact:
confidence:
review_status:
```

---

## 3.4 Tier 3 — Wiki Meta / Archive Patch Notes

Process later:

```text
Guild Wars 2 Wiki
Community portal
Help Editing
Recent changes
Quick access links
Admin noticeboard
Reporting wiki bugs
2017–2023 Game Update Notes
```

Expected outputs:

```text
docs/knowledge_base/source_registry/wiki_source_policy.md
docs/knowledge_base/source_registry/wiki_editability_note.md
docs/knowledge_base/source_registry/wiki_reliability_note.md
docs/knowledge_base/patch_notes/archive/
```

---

## 3.5 Tier 4 — Low Priority Archive

Archive for now:

```text
Gallant Longbow Skin
API talk_2
Editing API talk_2
unrelated individual item pages
```

Expected action:

```text
Move to _sources/pdf/low_priority/
Do not extract unless future feature requires it.
```

---

# 4. Recommended Directory Reorganization

The current directory is too flat:

```text
docs/knowledge_base/official/
```

Recommended source artifact structure:

```text
docs/knowledge_base/_sources/pdf/
├── official_api/
│   ├── API_Main - Guild Wars 2 Wiki (GW2W).pdf
│   ├── API_2 - Guild Wars 2 Wiki (GW2W).pdf
│   ├── API_Best practices - Guild Wars 2 Wiki (GW2W).pdf
│   ├── API_API key - Guild Wars 2 Wiki (GW2W).pdf
│   ├── API_2_tokeninfo - Guild Wars 2 Wiki (GW2W).pdf
│   └── endpoints/
├── arenanet/
│   ├── ArenaNet-apikey.pdf
│   ├── ArenaNet-security.pdf
│   ├── ArenaNet-game content.pdf
│   └── ...
├── patch_notes/
│   ├── 2026/
│   ├── 2025/
│   ├── 2024/
│   └── archive_2017_2023/
├── wiki_meta/
│   ├── Guild Wars 2 Wiki.pdf
│   ├── Help_Editing.pdf
│   └── ...
└── low_priority/
    ├── Gallant Longbow Skin.pdf
    └── API talk_2.pdf
```

Recommended KnowledgeArticle output structure:

```text
docs/knowledge_base/official/
├── gw2_api_summary.md
├── api_v2_resource_model.md
├── api_rate_limit.md
├── api_scopes_and_tokeninfo.md
├── api_key_safety.md
├── arenanet_content_terms_summary.md
└── api_endpoints/

docs/knowledge_base/patch_notes/
├── 2026/
├── 2025/
├── 2024/
└── archive/
```

---

# 5. PDF Processing Pipeline

## 5.1 Pipeline Overview

```text
PDF Inventory
→ PDF Classification
→ PDF Text Extraction
→ Evidence Record
→ KnowledgeArticle Summary
→ Entity / Action Linking
→ Review
→ Publish
```

---

## 5.2 Step 1 — PDF Inventory

Generate:

```text
data/kb/pdf_inventory.csv
```

Recommended columns:

```csv
pdf_id,file_name,path,size_bytes,category,year,priority,status,sha256
```

Example:

```csv
pdf:api:v2,API_2 - Guild Wars 2 Wiki (GW2W).pdf,_sources/pdf/official_api/API_2...,721484,official_api,,P0,pending,
pdf:patch:2026-06-02,Game Update Notes_ June 2, 2026...,patch_notes/2026/...,547066,patch_note,2026,P2,pending,
```

---

## 5.3 Step 2 — PDF Classification

Classification rules:

```text
file name contains "API_2_"            → official_api_endpoint
file name contains "API_Main"          → official_api_overview
file name contains "API_Best practices"→ api_governance
file name contains "tokeninfo"         → api_permission
file name contains "API key"           → api_key
file name contains "ArenaNet"          → arenanet_policy
file name contains "Game Update Notes" → patch_note
file name contains "Guild Wars 2 Wiki" → wiki_meta
file name contains "Help_"             → wiki_meta
file name contains "Recent changes"    → wiki_meta
otherwise                              → low_priority
```

---

## 5.4 Step 3 — PDF Text Extraction

Extract text only for selected tiers first.

Priority:

```text
Batch 1: Tier 0
Batch 2: Tier 1
Batch 3: 2026/2025/2024 patch notes
```

Output:

```text
data/extracted/pdf_text/<pdf_id>.txt
```

Important rule:

```text
Extracted text is intermediate processing data.
Do not copy full extracted text into final KnowledgeArticle markdown.
```

---

## 5.5 Step 4 — Evidence Record

Every PDF gets an Evidence record.

Schema:

```yaml
Evidence:
  evidence_id: evidence:pdf:api_v2
  source_type: downloaded_pdf
  source_file: docs/knowledge_base/_sources/pdf/official_api/API_2 - Guild Wars 2 Wiki (GW2W).pdf
  original_url: null
  downloaded_at: 2026-06-16
  sha256: ...
  file_size: 721484
  category: official_api
  confidence: 0.95
```

Rules:

```text
1. No API keys.
2. No private player data.
3. Evidence links to PDF source artifact.
4. Evidence can link to KnowledgeArticle.
```

---

## 5.6 Step 5 — KnowledgeArticle Summary

Create one KnowledgeArticle per important source.

Example:

```yaml
kb_id: kb:official:api_v2
title: GW2 API v2 Summary
domain: official
content_type: source_note
summary: ...
source_refs:
  - evidence:pdf:api_v2
linked_actions:
  - VALIDATE_API_SCOPE
  - INGEST_SOURCE
review_status: reviewed
```

---

## 5.7 Step 6 — Entity / Action Linking

API documents link to:

```text
Entity:
api:gw2_v2
api_endpoint:/v2/account
api_endpoint:/v2/tokeninfo

Action:
VALIDATE_API_SCOPE
SYNC_ACCOUNT_SNAPSHOT
REFRESH_PUBLIC_STATIC_DATA
```

Patch documents link to:

```text
Entity:
Patch
Skill
Trait
Item
Build
MarketSignal

Action:
CHECK_PATCH
VERIFY_BUILD_UPDATED
WATCH_IMPACTED_ITEM
RECOMPUTE_GOAL_AFTER_PATCH
```

---

## 5.8 Step 7 — Review

Review status:

```text
draft
reviewed
deprecated
needs_update
conflict
```

Only `reviewed` or official high-confidence content can drive high-priority actions.

---

# 6. Batch Plan

## 6.1 Batch 1 — API Governance and Security

Process first:

```text
API_Main
API_2
API_Best practices
API_API key
API_2_tokeninfo
ArenaNet-apikey
ArenaNet-security
ArenaNet-game content
ArenaNet-overview
```

Expected outputs:

```text
gw2_api_summary.md
api_v2_resource_model.md
api_rate_limit.md
api_scopes_and_tokeninfo.md
api_key_safety.md
arenanet_content_terms_summary.md
```

---

## 6.2 Batch 2 — API Endpoint Docs

Process second:

```text
API_2_account
API_2_characters
API_2_account_wallet
API_2_account_bank
API_2_account_achievements
API_2_achievements
API_2_achievements_categories
API_2_achievements_daily
API_2_recipes
API_2_recipes_search
API_2_dailycrafting
API_2_commerce
```

Expected outputs:

```text
api_endpoints/account.md
api_endpoints/characters.md
api_endpoints/account_wallet.md
api_endpoints/account_bank.md
api_endpoints/account_achievements.md
api_endpoints/achievements.md
api_endpoints/achievements_categories.md
api_endpoints/achievements_daily.md
api_endpoints/recipes.md
api_endpoints/recipes_search.md
api_endpoints/dailycrafting.md
api_endpoints/commerce.md
```

---

## 6.3 Batch 3 — Recent Patch Notes

Process:

```text
2026 patch notes
2025 patch notes
2024 patch notes
```

Priority 2026 examples:

```text
Game Update Notes_ June 2, 2026
Game Update Notes_ May 12, 2026
Game Update Notes_ April 14, 2026
Game Update Notes_ March 31, 2026
Game Update Notes_ March 17, 2026
Game Update Notes_ February 24, 2026
Game Update Notes_ February 3, 2026
Game Update Notes_ January 13, 2026
```

Expected outputs:

```text
docs/knowledge_base/patch_notes/2026/*.md
docs/knowledge_base/patch_notes/2025/*.md
docs/knowledge_base/patch_notes/2024/*.md
```

---

## 6.4 Batch 4 — Wiki Meta and Archive

Process later:

```text
Guild Wars 2 Wiki
Community portal
Help Editing
Recent changes
Quick access links
Admin noticeboard
Reporting wiki bugs
2017–2023 patch notes
```

---

# 7. Implementation Modules

Suggested new package:

```text
src/gw2radar/kb_pdf/
├── pdf_inventory.py
├── pdf_classifier.py
├── pdf_text_extractor.py
├── pdf_evidence_writer.py
├── pdf_kb_summarizer.py
├── pdf_patch_note_parser.py
├── pdf_api_doc_parser.py
└── pdf_processing_report.py
```

---

## 7.1 PdfSourceRecord

```python
class PdfSourceRecord(BaseModel):
    pdf_id: str
    file_name: str
    source_path: str
    size_bytes: int
    category: str
    year: int | None
    priority: str
    status: str
    sha256: str | None
```

---

## 7.2 PdfProcessingStatus

```python
class PdfProcessingStatus(str, Enum):
    pending = "pending"
    extracted = "extracted"
    summarized = "summarized"
    reviewed = "reviewed"
    archived = "archived"
    ignored = "ignored"
```

---

## 7.3 PdfKnowledgeSummary

```python
class PdfKnowledgeSummary(BaseModel):
    pdf_id: str
    kb_id: str
    title: str
    domain: str
    summary: str
    key_entities: list[str]
    linked_actions: list[str]
    evidence_id: str
    review_status: str
```

---

# 8. Codex Task — First-Stage PDF Knowledge Source Processing

```text
Current project: GW2Radar

Task:
Implement first-stage PDF knowledge source processing pipeline.

Input:
Existing downloaded PDF files under docs/knowledge_base/official or docs/knowledge_base/_sources/pdf.

Goal:
Classify downloaded PDF sources, generate inventory, extract text for priority PDFs, create evidence records, and produce initial KnowledgeArticle markdown summaries for Tier 0 and Tier 1 documents.

Requirements:
1. Do not scrape the web.
2. Do not download new files.
3. Do not copy full PDF text into KB articles.
4. Preserve original PDFs as source artifacts.
5. Generate data/kb/pdf_inventory.csv.
6. Classify PDFs into:
   - official_api
   - official_api_endpoint
   - api_governance
   - api_permission
   - api_key
   - arenanet_policy
   - patch_note
   - wiki_meta
   - low_priority
7. Extract text only for Tier 0 and Tier 1 first.
8. Create evidence records with:
   - evidence_id
   - source_file
   - file_size
   - sha256
   - category
   - confidence
9. Create initial markdown summaries:
   - gw2_api_summary.md
   - api_v2_resource_model.md
   - api_rate_limit.md
   - api_scopes_and_tokeninfo.md
   - api_key_safety.md
   - api_endpoints/*.md
10. Do not include API keys or private player data.
11. Do not alter runtime product logic.
12. Add tests for classification rules and no full-text copy policy.

Acceptance:
- pdf_inventory.csv exists.
- Tier 0 / Tier 1 PDFs classified.
- Evidence records generated.
- Initial KB markdown summaries generated.
- Full PDF text is not copied into KB summaries.
- Patch notes are inventoried but not fully processed unless explicitly selected.
```

---

# 9. Tests

Required tests:

```text
tests/test_pdf_inventory.py
tests/test_pdf_classifier.py
tests/test_pdf_evidence_writer.py
tests/test_pdf_no_full_text_copy.py
tests/test_pdf_no_private_data.py
tests/test_pdf_api_doc_summary.py
tests/test_pdf_patch_note_inventory.py
```

Test cases:

```text
1. API_2 file classified as official_api.
2. API_2_account file classified as official_api_endpoint.
3. API_Best practices file classified as api_governance.
4. API_2_tokeninfo classified as api_permission.
5. ArenaNet files classified as arenanet_policy.
6. Game Update Notes files classified as patch_note.
7. Gallant Longbow Skin classified as low_priority.
8. SHA256 generated for every PDF.
9. Evidence contains source file, size, hash, category.
10. KnowledgeArticle summary does not copy full text.
11. No API key/private player data appears in generated KB files.
```

---

# 10. Acceptance Checklist

```text
Inventory:
- [ ] data/kb/pdf_inventory.csv exists.
- [ ] all PDFs from source directory are listed.
- [ ] each PDF has category, priority, and status.
- [ ] each PDF has sha256.

Organization:
- [ ] source PDFs are moved or mapped into _sources/pdf categories.
- [ ] Tier 0 and Tier 1 are identified.
- [ ] patch notes are grouped by year.

Evidence:
- [ ] Evidence records exist for Tier 0 and Tier 1.
- [ ] Evidence records reference PDF artifacts.
- [ ] Evidence records do not include private data.

Knowledge Base:
- [ ] Tier 0 summary markdown generated.
- [ ] Tier 1 endpoint markdown generated.
- [ ] No full PDF text copied.
- [ ] Markdown summaries link to evidence IDs.

Governance:
- [ ] no API keys.
- [ ] no private account data.
- [ ] no web scraping.
- [ ] no runtime behavior changed.

Tests:
- [ ] classification tests pass.
- [ ] evidence tests pass.
- [ ] no-full-text-copy tests pass.
```

---

# 11. Final Recommendation

The 216 downloaded PDFs should be processed as follows:

```text
Immediate:
API / tokeninfo / best practices / API key / ArenaNet security

Second:
account / characters / wallet / bank / achievements / recipes / commerce endpoint docs

Third:
2026 / 2025 / 2024 Game Update Notes

Later:
2017–2023 Game Update Notes
Wiki help/community/recent changes

Archive:
Gallant Longbow Skin
API talk pages
editing pages
```

Final rule:

```text
PDF original = Evidence Source Artifact
Extracted text = intermediate processing data
Markdown summary = KnowledgeArticle
Structured fields = Graph / EndpointSchema / PatchImpact
Expert rule = KnowledgeRule
```

Do not turn raw PDFs into direct product knowledge without classification, evidence, summarization, graph linking, and review.
