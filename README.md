# GW2Radar MVP 0.1

Legendary Goal Intelligence Edition.

Before development, read:

- `GW2RADAR_PROJECT_CONSTITUTION.md`
- `GW2RADAR_API_ACCESS_GOVERNANCE.md`
- `docs/mvp/MVP_0_1_CODEX_DEVELOPMENT_SPEC.md`

This MVP validates one deterministic mock loop:

```text
player goal -> requirements -> owned resources -> gap -> actions -> Markdown report
```

Run tests:

```bash
pytest
python harness/run_smoke.py
python -m alembic upgrade head
```

Run API:

```bash
uvicorn gw2radar.api.main:app --reload
```

Runtime configuration:

```bash
set GW2RADAR_DATABASE_URL=sqlite:///./gw2radar.db
```

`/mock/load` writes the deterministic mock graph into SQLite. API reads can rebuild
the in-process graph from persisted data after the process cache is reset.

Generate a local report package:

```http
POST /reports/gw2:goal:aurora/export-package
```

Graph data is separated with `graph_layer` values:

- `public_game`
- `private_player_state`
- `personal_intelligence`

GW2 API access remains behind `Gw2ApiGateway`. MVP gateway contracts include enum statuses, endpoint TTL resolution, batch helper support, and retry metadata, but no real network client is enabled by default.
