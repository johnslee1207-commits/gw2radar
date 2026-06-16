# GW2Radar Project Index

This index is the navigation entry point for the GW2Radar repository.

## Governance

- [Project Constitution](GW2RADAR_PROJECT_CONSTITUTION.md)
- [API Access Governance](GW2RADAR_API_ACCESS_GOVERNANCE.md)
- [Agent Instructions](AGENTS.md)

## Product And Architecture

- [Product Requirements](docs/PRD.md)
- [Software Design](docs/SDD.md)
- [Harness Guide](docs/HARNESS.md)
- [Prompt Notes](docs/PROMPTS.md)
- [Loop Notes](docs/LOOPS.md)

## Knowledge Base

- [Knowledge Base Overview](docs/knowledge_base/README.md)

The Knowledge Base explains recommendations, while the Knowledge Graph reasons over entities, relations, evidence, and player state.

## Ontology

- [GW2 Ontology Core](docs/ontology/GW2_ONTOLOGY_CORE.md)
- [Entity Types](docs/ontology/ENTITY_TYPES.md)
- [Relation Types](docs/ontology/RELATION_TYPES.md)
- [Attribute Schema](docs/ontology/ATTRIBUTE_SCHEMA.md)
- [Action Schema](docs/ontology/ACTION_SCHEMA.md)
- [Inference Rules](docs/ontology/INFERENCE_RULES.md)

## Graph

- [Graph Pipeline](docs/graph/GRAPH_PIPELINE.md)
- [Legendary Goal Graph](docs/graph/LEGENDARY_GOAL_GRAPH.md)
- [Graph Layer Separation](docs/graph/GRAPH_LAYER_SEPARATION.md)
- [Evidence Model](docs/graph/EVIDENCE_MODEL.md)

## MVP Milestones

- [MVP 0.1 Codex Development Spec](docs/mvp/MVP_0_1_CODEX_DEVELOPMENT_SPEC.md)
- [MVP 0.1 Legendary Goal](docs/mvp/MVP_0_1_LEGENDARY_GOAL.md)
- [MVP 0.1.2 Report Export Package](docs/mvp/MVP_0_1_2_REPORT_EXPORT_PACKAGE.md)
- [MVP 0.1.3 Graph Layer Separation](docs/mvp/MVP_0_1_3_GRAPH_LAYER_SEPARATION.md)
- [MVP 0.1.4 Gateway Contract Hardening](docs/mvp/MVP_0_1_4_GATEWAY_CONTRACT_HARDENING.md)
- [MVP 0.1.5 Evidence Quality Rules](docs/mvp/MVP_0_1_5_EVIDENCE_QUALITY_RULES.md)
- [MVP 0.1.6 Real GW2 API Client Skeleton](docs/mvp/MVP_0_1_6_REAL_GW2_API_CLIENT_SKELETON.md)
- [MVP 0.1.7 API Key And Snapshot Lifecycle](docs/mvp/MVP_0_1_7_API_KEY_AND_SNAPSHOT_LIFECYCLE.md)
- [MVP 0.1.8 Durable Queue And Sync Workers](docs/mvp/MVP_0_1_8_DURABLE_QUEUE_AND_SYNC_WORKERS.md)
- [MVP 0.1.9 Refresh Queue Detailed Contract](docs/mvp/MVP_0_1_9_REFRESH_QUEUE_DETAILED_CONTRACT.md)
- [MVP 0.2.0 Official API Compatibility Hardening](docs/mvp/MVP_0_2_0_OFFICIAL_API_COMPATIBILITY_HARDENING.md)
- [MVP 0.2.1 Account Sync API Productization](docs/mvp/MVP_0_2_1_ACCOUNT_SYNC_API_PRODUCTIZATION.md)
- [MVP 0.2.2 Public Static Refresh Planner](docs/mvp/MVP_0_2_2_PUBLIC_STATIC_REFRESH_PLANNER.md)
- [MVP 0.2.3 Release Readiness Hardening](docs/mvp/MVP_0_2_3_RELEASE_READINESS_HARDENING.md)
- [MVP 0.2.4 Production Security Upgrade](docs/mvp/MVP_0_2_4_PRODUCTION_SECURITY_UPGRADE.md)
- [MVP 0.3.0 Paid Report Engine](docs/mvp/MVP_0_3_0_PAID_REPORT_ENGINE.md)
- [MVP 0.3.1 Legendary Planner Pro](docs/mvp/MVP_0_3_1_LEGENDARY_PLANNER_PRO.md)
- [MVP 0.3.2 Build Fit Advisor](docs/mvp/MVP_0_3_2_BUILD_FIT_ADVISOR.md)
- [MVP 0.3.3 Market Radar Pro](docs/mvp/MVP_0_3_3_MARKET_RADAR_PRO.md)
- [MVP 0.3.4 Growth CMS Payment](docs/mvp/MVP_0_3_4_GROWTH_CMS_PAYMENT.md)
- [MVP 0.3.5 Guild Readiness Console](docs/mvp/MVP_0_3_5_GUILD_READINESS_CONSOLE.md)
- [MVP 0.3.6 Creator Intelligence Console](docs/mvp/MVP_0_3_6_CREATOR_INTELLIGENCE_CONSOLE.md)
- [MVP 0.3.7 KB Core Schema Source Registry](docs/mvp/MVP_0_3_7_KB_CORE_SCHEMA_SOURCE_REGISTRY.md)
- [MVP 0.3.8 KB Repository Markdown API](docs/mvp/MVP_0_3_8_KB_REPOSITORY_MARKDOWN_API.md)
- [MVP 0.3.9 KB Source Registry Domain Seeds](docs/mvp/MVP_0_3_9_KB_SOURCE_REGISTRY_DOMAIN_SEEDS.md)
- [MVP 0.4.0 KB Entity Linker Rule Distiller](docs/mvp/MVP_0_4_0_KB_ENTITY_LINKER_RULE_DISTILLER.md)
- [MVP 0.4.1 KB-backed Recommendation Explanations](docs/mvp/MVP_0_4_1_KB_BACKED_RECOMMENDATION_EXPLANATIONS.md)
- [MVP 0.4.2 KB-backed Paid Report Artifacts](docs/mvp/MVP_0_4_2_KB_BACKED_PAID_REPORT_ARTIFACTS.md)

## Analysis And Maturity

- [All-Stage Code Semantic Maturity Audit](docs/analysis/ALL_STAGE_CODE_SEMANTIC_MATURITY_AUDIT.md)
- [Code Spectrum And Semantic Graph](docs/analysis/CODE_SPECTRUM_AND_SEMANTIC_GRAPH.md)
- [GitNexus MVP Maturity Analysis](docs/analysis/GITNEXUS_MVP_MATURITY_ANALYSIS.md)
- [Post-MVP Graph Maturity And Roadmap](docs/analysis/POST_MVP_GRAPH_MATURITY_AND_ROADMAP.md)
- [Semantic Graph JSON](docs/analysis/semantic_graph.json)
- [GitNexus Semantic Graph Snapshot](docs/analysis/gitnexus_semantic_graph_snapshot.json)

## Verification

Primary commands:

```bash
python -m pytest
python harness/run_smoke.py
python harness/run_sync_smoke.py
python -m alembic upgrade head
```
