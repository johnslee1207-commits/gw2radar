# GW2Radar Player UI Guide

## Entry Point

Start the API server and open `/player`. The page is a player cockpit for the three commercial opportunities already implemented by the backend:

- Returner Diagnosis
- Legendary Planner Pro
- Build Fit Advisor

The UI is intentionally account-first. It shows account connection, sync state, data freshness, safety boundaries, and the next manual action before exposing report or market controls.

## Start The System

From the repository root:

```bash
python -m uvicorn gw2radar.api.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/player
```

For local development without a real GW2 API key, open `Connect` and use `Load demo graph` before testing Returner, Legendary, Build Fit, and Reports flows.

## First Use

1. Open `Welcome`.
2. Choose the player intent for this session.
3. Open `Connect`.
4. Paste a GW2 API key and save it.
5. Check key status.
6. Check permissions and review missing required or optional scopes.
7. Queue account sync only after the permission grid is ready or you accept limited mode.
8. Drain one sync job in local development.
9. Open `Freshness`.
10. Return to `Dashboard` and refresh status.

The API key is cleared from the browser input after submission. The backend status endpoint never returns the raw key.
The permission inspection endpoint returns only token metadata, granted permissions, missing permissions, feature impact, and safety boundaries. It never returns the raw key.
The sync status expands the account job into endpoint-level progress for account profile, characters, wallet, materials, bank, and achievements.

## State Recovery

The browser stores only lightweight UI state:

- Active page.
- Last imported build id.

It does not store the GW2 API key. Deleting browser storage only resets UI convenience state; it does not delete backend account snapshots or encrypted key storage. Use `Privacy` for backend deletion controls.

## Daily Use

1. Review `Today’s Best Actions`.
2. Review `This Week` actions and source confidence before committing to longer routes.
3. Use `Returner` to inspect goal gaps, a short action plan, preview, and full report export.
4. Use `Legendary` before selling materials.
5. Use `Build Fit` before converting gear. Synced official API character snapshots appear first when account sync has character detail; item and stat names are enriched from public `/v2/items` and `/v2/itemstats` metadata when available. Manual samples remain available as fallback.
6. Use `Freshness` before following account-aware or market-aware advice.
7. Use `Reports` to preview, unlock, retrieve artifacts, and reopen local report history.

Each workflow displays a short result summary above the raw JSON output. The summary is for navigation only; the raw JSON and generated report remain the authoritative output.

## Legendary Goal Choices

The Legendary view can load the player-facing goal catalog:

- Aurora
- Vision
- Conflux
- Ad Infinitum
- Legendary Weapon
- Legendary Armor
- Custom Goal

Use `Today / this week` after loading or adding goals to compare cheap, fast, and balanced routes.

## Freshness And Confidence

Dashboard, Freshness, preview reports, and full reports expose source confidence annotations. Treat stale account snapshots, manual market snapshots, old build sources, or unreviewed knowledge rules as manual-review signals.

## Data Management

The `Privacy` page provides:

- Delete API key.
- Delete account snapshot.
- Delete all private data.

The full private data deletion action also clears local build/report convenience state in the browser.

## Safety Boundaries

- No gameplay automation.
- No automatic trading.
- No guaranteed market return claims.
- No absolute meta claims.
- Private account data stays separate from public KB and market evidence.
