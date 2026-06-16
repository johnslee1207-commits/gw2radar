# MVP 0.1.3 Graph Layer Separation

MVP 0.1.3 implements the Constitution requirement that public game facts, private player state, and derived personal intelligence remain separated.

## Layers

```text
public_game
private_player_state
personal_intelligence
```

## Implemented Objects

The following schemas include `graph_layer`:

- `Entity`
- `Relation`
- `Evidence`
- `PlayerState`
- `Action`

The following SQLAlchemy tables include `graph_layer`:

- `entities`
- `relations`
- `evidence`
- `player_state`
- `actions`

## Enforcement

`GraphRepository.replace_graph()` validates graph layers before persistence.

Hard checks:

- account entities must be private;
- player state rows must be private;
- `OWNED_BY` relations must be private;
- `MISSING_FOR_GOAL` and `ADVANCES_GOAL` relations must be personal intelligence;
- actions must be personal intelligence.

## Verification

Covered by:

- `tests/test_graph_layers.py`
- `python harness/run_smoke.py`
- `python -m alembic upgrade head`
