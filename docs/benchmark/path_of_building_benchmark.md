# Path of Building Benchmark

## Reference Links

- https://pathofbuilding.community/
- https://github.com/PathOfBuildingCommunity/PathOfBuilding

## Core Features

- Deep structured build planner.
- Equipment, skills, passive choices, buffs, and configuration produce explainable calculations.
- Players can inspect breakdowns and compare alternatives.
- Build data is versioned and community-maintained.

## Data Model Signals

- `Build`: profession, specialization, role, game mode, source, patch version, difficulty, requirements, review status.
- `BuildRequirement`: slot, item type, stat combo, rarity minimum, acceptable alternatives, required flag, estimated cost.
- `BuildFitBreakdown`: reusable gear, missing gear, wrong stats, missing upgrades, transition cost, patch warning.

## Strengths

- Excellent structured computation and breakdown visibility.
- Strong version awareness.
- Supports expert users who need detailed tradeoff inspection.

## Weaknesses For GW2Radar Positioning

- Full combat simulation would be too complex for early GW2Radar.
- It can overwhelm players who only need account-to-build fit.

## What GW2Radar Should Copy

- Treat builds as structured objects, not copied text.
- Explain why each missing slot affects readiness.
- Preserve formula and breakdown visibility.

## What GW2Radar Should Avoid

- Claiming full DPS simulation or absolute meta truth.
- Expanding into a hard-core simulator before account fit, source freshness, and evidence gates are mature.

## Differentiation

GW2Radar should provide Build Fit computation: whether this account can play this build, what can be reused, what is missing, what it costs, and whether the source needs patch review.

