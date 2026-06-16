# GW2Radar MVP 0.1 Codex Development Spec

Before implementing any feature, read and comply with:

1. `GW2RADAR_PROJECT_CONSTITUTION.md`
2. `GW2RADAR_API_ACCESS_GOVERNANCE.md`
3. `docs/ontology/GW2_ONTOLOGY_CORE.md`
4. `docs/ontology/ACTION_SCHEMA.md`
5. `docs/mvp/MVP_0_1_LEGENDARY_GOAL.md`

Current MVP loop:

```text
Goal -> Requirements -> Player State -> Missing -> Action -> Recommendation -> Report
```

Do not implement:

- gameplay automation;
- client memory reading;
- game client modification;
- automated trading;
- RMT support;
- proxy pools;
- IP rotation;
- GW2 API rate-limit evasion;
- plaintext API key logging;
- private player data leakage into public game graph.

Required implementation posture:

- Constitution first.
- Ontology second.
- Implementation third.
- Commercialization last.

Every task must include tests or smoke harness coverage and must preserve the recommendation-only boundary.
