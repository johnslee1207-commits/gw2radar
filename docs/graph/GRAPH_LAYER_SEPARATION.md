# Graph Layer Separation

GW2Radar keeps three graph layers separate:

- `public_game`: public GW2 facts such as goals, requirements, items, currencies, achievements, and tasks.
- `private_player_state`: player-authorized account facts such as account entity, owned quantities, wallet/material state, and `OWNED_BY` relations.
- `personal_intelligence`: derived recommendations and analysis such as missing requirements, action recommendations, and `ADVANCES_GOAL` relations.

## Current Enforcement

The following objects carry `graph_layer`:

- `Entity`
- `Relation`
- `Evidence`
- `PlayerState`
- `Action`

The SQLAlchemy persistence models also include `graph_layer`, added by Alembic migration `0003_add_graph_layer_fields`.

`GraphRepository.replace_graph()` validates layers before writing:

- `PlayerState` must be `private_player_state`.
- `ACCOUNT` entities must be `private_player_state`.
- `OWNED_BY` relations must be `private_player_state`.
- `MISSING_FOR_GOAL` and `ADVANCES_GOAL` relations must be `personal_intelligence`.
- `Action` records must be `personal_intelligence`.

## MVP Mock Layer Mapping

| Object | Layer |
|---|---|
| Aurora goal | `public_game` |
| Items/currencies/achievements/tasks | `public_game` |
| REQUIRES / PRODUCES relations | `public_game` |
| Mock account entity | `private_player_state` |
| PlayerState rows | `private_player_state` |
| OWNED_BY relations | `private_player_state` |
| MISSING_FOR_GOAL relations | `personal_intelligence` |
| ADVANCES_GOAL relations | `personal_intelligence` |
| Actions | `personal_intelligence` |

This implementation prevents private player state from being persisted as public game graph data.
