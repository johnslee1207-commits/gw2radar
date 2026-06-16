# GW2Radar Ontology Core

MVP 0.1 models personal Legendary goal intelligence with five object families:

- Entity: game objects such as account, goal, item, currency, achievement, task, action, and evidence.
- Attribute: typed properties stored on entities and relations.
- Relation: graph edges such as REQUIRES, PRODUCES, MISSING_FOR_GOAL, ADVANCES_GOAL, and OWNED_BY.
- Action: explainable manual recommendations such as HOLD, DO_DAILY, BUY, FARM, or COMPLETE_ACHIEVEMENT.
- Evidence: source metadata for mock fixtures or future API reads.

All MVP recommendations are informational. The system must not automate gameplay, trading, client control, or order placement.

All core graph objects carry a `graph_layer` value so public game facts, private player state, and derived personal intelligence remain separated.
