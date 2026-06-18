# Player UI Information Architecture

## Navigation

- `Dashboard`: account snapshot, today actions, commercial opportunity cards, do-not-sell warning.
- `Connect`: API key save/delete, sync queue, local drain-one, demo graph load.
- `Returner`: goal loading, Aurora gap, action generation, KB-backed report preview.
- `Legendary`: portfolio, recompute, do-not-sell, market snapshots, watchlist, goal cost index.
- `Build Fit`: build import, build list, fit score, transition plan, patch freshness, build report.
- `Reports`: products, pricing, mock checkout, job lookup, artifact open.
- `Privacy`: safety boundaries, key deletion, account snapshot deletion.

## Runtime Entry

- API app: `gw2radar.api.main:app`
- Local server command: `python -m uvicorn gw2radar.api.main:app --reload`
- Player UI route: `/player`
- Static asset mount: `/player-ui`

## UI State

- Active view is stored in `localStorage` under `gw2radar.player.activeView`.
- Last imported build id is stored in `localStorage` under `gw2radar.player.activeBuildId`.
- API key material is never stored in browser state.
- Backend deletion controls remain under `Privacy`.

## Semantic Model

- `Account` provides private state and freshness.
- `Goal` anchors returner and legendary workflows.
- `Requirement` links goals, gear, and market items.
- `Build` links player intent to reusable gear and missing gear.
- `MarketSnapshot` informs observation-only price context.
- `ReportJob` turns analysis into player-facing artifacts.
- `KnowledgeRule` explains recommendations with reviewed evidence.

## Code Graph Anchors

- UI route: `src/gw2radar/api/routes/player_ui.py`
- FastAPI mount: `src/gw2radar/api/main.py`
- Static assets: `src/gw2radar/ui/static/`
- Account routes: `src/gw2radar/api/routes/account.py`
- Sync routes: `src/gw2radar/api/routes/account_sync.py`
- Legendary routes: `src/gw2radar/api/routes/legendary.py`
- Build routes: `src/gw2radar/api/routes/builds.py`
- Market routes: `src/gw2radar/api/routes/market.py`
- Report routes: `src/gw2radar/api/routes/reports.py`
