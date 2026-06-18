# Snow Crows Benchmark

## Reference Links

- https://snowcrows.com/
- https://snowcrows.com/builds
- https://snowcrows.com/builds/open-world
- https://snowcrows.com/guides/builds

## Core Features

- High-quality GW2 build and guide source.
- Organized by profession, specialization, role, and game mode.
- Strong version and patch awareness.
- Useful beginner, open-world, raid, fractal, and strike context.

## Data Model Signals

- `BuildSource`: source id, source name, source URL, allowed use, attribution, crawl policy, review required.
- `BuildMetadata`: build name, profession, specialization, game mode, role, difficulty, patch version, source last seen, review status.
- `PatchReviewSignal`: affected profession, skill, trait, or build family.

## Strengths

- Expert-quality build knowledge.
- Strong role and encounter awareness.
- Source freshness matters to users.

## Weaknesses For GW2Radar Positioning

- Third-party guide content cannot be copied into GW2Radar.
- Expert builds do not automatically answer whether a specific account can play them.

## What GW2Radar Should Copy

- Metadata structure: role, profession, specialization, game mode, patch awareness, source attribution.
- Respect for expert review and update cycles.

## What GW2Radar Should Avoid

- Copying complete guide text.
- Presenting expert builds as account-ready without fit checks.
- Strong recommendations from unreviewed source metadata.

## Differentiation

GW2Radar should use Snow Crows-like build sources as attributed metadata and reviewed references, then calculate personal account fit and transition cost.

