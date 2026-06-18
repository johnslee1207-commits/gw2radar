# gw2efficiency Benchmark

## Reference Links

- https://gw2efficiency.com/
- https://gw2efficiency.com/crafting/calculator
- https://gw2efficiency.com/user/api-keys
- https://gw2efficiency.com/frequently-asked-questions

## Core Features

- API-key based account exploration.
- Account assets, wallet, bank, material storage, and character context.
- Crafting calculator with cost breakdown, owned material usage, shopping list, and crafting steps.
- Account value and progress-oriented dashboards.

## Data Model Signals

- `AccountSnapshot`: account identity, sync freshness, wallet, characters, bank, material storage, achievements, equipment.
- `AccountInventoryIndex`: item id, total quantity, storage locations, reserved quantity, surplus quantity.
- `ShoppingListItem`: missing item, quantity, estimated price, source, urgency.
- `DoNotSellItem`: reserved goal, required quantity, owned quantity, safe surplus.

## Strengths

- Mature account data ingestion and asset visibility.
- Strong crafting and shopping-list workflows.
- Clear relationship between official API data and account planning.

## Weaknesses For GW2Radar Positioning

- Primarily answers what the account owns.
- Less focused on narrative next-step coaching and evidence-backed paid reports.

## What GW2Radar Should Copy

- Account data trust model based on official API key scopes.
- Unified inventory/material/wallet indexing.
- Owned-material reuse and missing-material shopping-list semantics.
- Clear freshness and sync status language.

## What GW2Radar Should Avoid

- Becoming only an asset explorer.
- Treating account value as the main product promise.
- Exposing raw private account payloads in reports or public knowledge.

## Differentiation

GW2Radar should use gw2efficiency-grade account data as foundation, then answer what the player should do next for active goals, do-not-sell protection, build fit, and reports.

