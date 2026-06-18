# Wowhead Planner Benchmark

## Reference Links

- https://www.wowhead.com/
- https://www.wowhead.com/planner
- https://www.wowhead.com/help=character-planner

## Core Features

- Player-facing database and guide experience.
- Character or profile context drives personalized recommendations.
- Content, gear, achievement, and profession guidance is translated into user-facing next steps.

## Data Model Signals

- `AccountReadiness`: travel, combat, progression, build, legendary, group content, WvW, and overall scores.
- `ReturnerProfile`: last played band, interests, strongest character, playable modes, blocked modes, missing unlocks.
- `ReturnerPlan`: 7-day or 30-day actions, reasons, expected gain, evidence refs.

## Strengths

- Strong player-language UX.
- Users do not need to understand the underlying database schema.
- Good pattern for turning state into content recommendations.

## Weaknesses For GW2Radar Positioning

- WoW-specific ecosystem and content model.
- More guide/database oriented than private GW2 account graph oriented.

## What GW2Radar Should Copy

- Start from player intent and character/account readiness.
- Present recommendations as plain next steps.
- Keep onboarding friendly for returning players.

## What GW2Radar Should Avoid

- Hiding evidence and assumptions behind polished language.
- Making Returner Diagnosis depend on one legendary goal such as Aurora.

## Differentiation

GW2Radar should build an independent Returner Account Advisor that works from synced GW2 account state, explains readiness dimensions, and generates account-safe recovery plans.

