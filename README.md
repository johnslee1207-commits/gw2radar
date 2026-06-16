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
```

Run API:

```bash
uvicorn gw2radar.api.main:app --reload
```
