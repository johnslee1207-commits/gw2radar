# GW2Radar MVP 0.1

Legendary Goal Intelligence Edition.

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
