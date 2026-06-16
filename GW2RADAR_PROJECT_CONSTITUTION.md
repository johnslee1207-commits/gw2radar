# GW2Radar Project Constitution

GW2Radar is a Guild Wars 2 personal intelligence and decision-support system. It combines public game data, player-authorized account snapshots, ontology, graph inference, action recommendations, and evidence-backed reports.

This constitution has priority over feature requests, implementation shortcuts, and commercialization plans.

## Mission

GW2Radar helps players understand:

- what to do today or this week;
- what is missing for an active goal;
- which materials should be kept;
- which surplus materials may be considered for sale;
- which evidence supports each recommendation.

## Red Lines

GW2Radar must not:

- automate gameplay;
- log into or control the game client;
- read or modify game client memory;
- simulate keyboard, mouse, chat, trading, crafting, gathering, combat, or movement;
- support RMT, gold selling, account selling, boosting, or power leveling;
- bypass GW2 API rate limits;
- use proxy pools or IP rotation;
- store API keys in logs, reports, raw evidence, or test snapshots;
- mix private player data into public game knowledge;
- present low-confidence information as certain fact;
- describe market signals as guaranteed profit.

## Graph Separation

GW2Radar keeps three graph layers separate:

- Public Game Graph: public items, recipes, achievements, currencies, patches, prices, and sources.
- Private Player State Graph: player-authorized account, inventory, wallet, progression, characters, and active goals.
- Personal Intelligence Graph: derived gaps, reserved materials, recommendations, and reports.

Private player state must not flow into public game graph datasets, shared trends, or training data without explicit authorization.

## Recommendation Boundary

Actions are recommendations only. They may suggest manual farming, holding, buying, crafting, daily tasks, weekly tasks, achievement completion, or report generation.

Actions must not execute buys, sells, crafts, gameplay inputs, or client interactions.

## Constitution Compliance Check

Every implementation task must check:

- Does not automate gameplay.
- Does not interact with the game client.
- Does not read or modify game memory.
- Does not support RMT, gold selling, account selling, or boosting.
- Does not bypass GW2 API rate limits.
- Does not implement proxy pools or IP rotation.
- All external GW2 API calls go through `Gw2ApiGateway`.
- API keys are never logged or stored in raw evidence.
- Private player data is separated from public game graph data.
- Important relations and recommendations include evidence references when available.
- Action outputs are recommendations only.
- Market language avoids guaranteed-profit claims.
- Low-confidence data is marked as low-confidence.
