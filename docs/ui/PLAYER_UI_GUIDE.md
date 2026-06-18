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
6. Queue account sync.
7. Drain one sync job in local development.
8. Open `Freshness`.
9. Return to `Dashboard` and refresh status.

The API key is cleared from the browser input after submission. The backend status endpoint never returns the raw key.

## State Recovery

The browser stores only lightweight UI state:

- Active page.
- Last imported build id.

It does not store the GW2 API key. Deleting browser storage only resets UI convenience state; it does not delete backend account snapshots or encrypted key storage. Use `Privacy` for backend deletion controls.

## Daily Use

1. Review `Today’s Best Actions`.
2. Use `Returner` to inspect goal gaps and a short action plan.
3. Use `Legendary` before selling materials.
4. Use `Build Fit` before converting gear.
5. Use `Freshness` before following account-aware or market-aware advice.
6. Use `Reports` to preview, unlock, retrieve artifacts, and reopen local report history.

Each workflow displays a short result summary above the raw JSON output. The summary is for navigation only; the raw JSON and generated report remain the authoritative output.

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
