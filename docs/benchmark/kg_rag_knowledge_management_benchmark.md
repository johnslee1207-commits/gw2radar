# KG/RAG Knowledge Management Benchmark

## Reference Links

- https://en.wikipedia.org/wiki/Knowledge_graph
- https://en.wikipedia.org/wiki/Retrieval-augmented_generation

## Core Features

- Raw evidence is converted into curated knowledge.
- Knowledge graph entities and relations support structured reasoning.
- RAG explains reviewed evidence; it does not invent source facts.
- Rules and review gates prevent unsupported recommendations.

## Data Model Signals

- `RawEvidence`: source id, source URL, file hash, summary, confidence, freshness, privacy marker.
- `KnowledgeArticle`: domain, content type, summary, linked entities, linked actions, source refs, review status.
- `KnowledgeRule`: condition, recommendation, action type, priority delta, evidence refs, review status, enabled flag.
- `ReportEvidenceFormatter`: assumptions, source refs, freshness, reviewer state, private/public boundary.

## Strengths

- Traceability from report output to evidence.
- Clear public/private data separation.
- Supports audit, freshness, and rule promotion workflows.

## Weaknesses For GW2Radar Positioning

- Generic RAG can sound convincing without grounded decision logic.
- Search-only explanations do not replace account-state reasoning.

## What GW2Radar Should Copy

- Evidence-first ingestion.
- Reviewed article and rule promotion.
- Explanation layers that cite evidence and assumptions.
- Freshness and confidence signals in paid reports.

## What GW2Radar Should Avoid

- Letting LLM output create facts or override graph/rule decisions.
- Mixing private account data into public KB.
- Allowing expired, unreviewed, or low-confidence evidence to drive strong paid recommendations.

## Differentiation

GW2Radar should use KG/RAG as a trusted explanation layer over graph, player state, and reviewed rules, not as the decision engine itself.

