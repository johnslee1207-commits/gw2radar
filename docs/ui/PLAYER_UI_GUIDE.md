# GW2Radar Player UI Guide

## Entry Point

Start the API server and open `/player`. The page is a player cockpit for the three commercial opportunities already implemented by the backend:

- Returner Diagnosis
- Legendary Planner Pro
- Build Fit Advisor

The UI is intentionally account-first. It shows account connection, sync state, data freshness, safety boundaries, and the next manual action before exposing report or market controls.

## First Use

1. Open `Connect`.
2. Paste a GW2 API key and save it.
3. Check key status.
4. Queue account sync.
5. Drain one sync job in local development.
6. Return to `Dashboard` and refresh status.

The API key is cleared from the browser input after submission. The backend status endpoint never returns the raw key.

## Daily Use

1. Review `Today’s Best Actions`.
2. Use `Returner` to inspect goal gaps and a short action plan.
3. Use `Legendary` before selling materials.
4. Use `Build Fit` before converting gear.
5. Use `Reports` to preview, unlock, and retrieve artifacts.

## Safety Boundaries

- No gameplay automation.
- No automatic trading.
- No guaranteed market return claims.
- No absolute meta claims.
- Private account data stays separate from public KB and market evidence.
