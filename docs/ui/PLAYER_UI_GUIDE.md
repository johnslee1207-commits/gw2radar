# GW2Radar Player UI Guide

## Entry Point

Start the API server and open `/player`. The page is a player cockpit for the three commercial opportunities already implemented by the backend:

- Returner Diagnosis
- Legendary Planner Pro
- Achievement Route Planner
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

For an automated local regression of the same player path, run:

```bash
python harness/run_player_ui_e2e_smoke.py
```

The harness verifies the cockpit shell, demo graph, build import, reviewed
upgrade-rule import and enable gate, Build Fit KB evidence, paid report
generation, and artifact retrieval. The route planner has a focused smoke path:

```bash
python harness/run_achievement_route_smoke.py
```

It verifies the route UI marker, reviewed route source ingestion, official
achievement detail draft preview, official achievement id fetch orchestration,
deterministic route API, ready/blocked/time-gated classification, Markdown
assumptions, CSV export, and manual-planning boundary.

When a real API key appears to save successfully but no account-aware result
appears, run:

```bash
python harness/run_account_connection_diagnostic.py
```

This diagnostic verifies key normalization, permission inspection, sync queue
status, drain-one execution, private account snapshot writes, synced character
snapshot exposure, and Build Fit gear conversion. A failing step points to the
layer that needs investigation: key format, permissions, queue orchestration,
private graph persistence, or UI snapshot bridging.
The Connect page also includes a read-only `Run connection diagnostic` action
that surfaces the same lifecycle as PASS/WARN/FAIL checks without returning the
raw API key or private item payloads.
Each failing or warning diagnostic card includes a concrete fix action when the
next step is available in the UI, such as updating the key, running sync,
draining one local job, or loading Build Fit character snapshots. Missing
required scopes are named directly, for example `characters`, so players can
regenerate the key instead of guessing why no account-aware output appeared.
Use `Export debug bundle` when you need to share a troubleshooting snapshot. The
bundle includes key status, missing permissions, sync status, diagnostic checks,
snapshot counts, and lightweight UI state. It excludes the raw API key, local
build ids, private inventory/material/bank/wallet payloads, character equipment
payloads, and report artifact contents.
Support or development reviewers can inspect an exported bundle locally with:

```bash
python harness/run_account_debug_bundle_review.py path/to/account_debug_bundle.json
```

They can also open the local support workbench after starting the API server:

```text
http://127.0.0.1:8000/support
```

The review classifies common "saved but no result" cases: missing key, missing
permissions, delayed sync, sync not queued, private snapshot not written, synced
character snapshot missing, Build Fit snapshot not loaded, or backend ready while
the player UI flow is still incomplete. The support page renders the same result,
evidence paths, and a reply template that preserves the no-secret boundary.
Reviewers can save a case audit record after review. The audit stores status,
finding ids, reviewer, timestamp, evidence paths, and a short reply summary only;
it does not store the raw bundle, raw API key, local build ids, private account
payloads, or report contents. The support workbench can filter audit records by
status, severity, and reviewer, then export the same privacy-safe metadata as
CSV for support trend analysis. The metrics summary aggregates matching audit
records into total cases, status counts, severity counts, finding counts, top
blockers, and a short trend sentence so support can prioritize real connection
failure causes without reading raw bundles. The remediation playbook maps top
blockers to support steps, safe player reply templates, evidence paths, and
product fix suggestions. The product backlog generator turns those product
suggestions into ranked backlog items with affected case counts, support signal,
and acceptance criteria. The backlog can be exported as Markdown for issue or
roadmap drafting, or CSV for triage spreadsheets. Reviewers can also promote a
ranked backlog item into a draft roadmap/issue artifact from the support
workbench, then list or export those drafts as Markdown or CSV. Drafts can be
marked `accepted`, `linked`, or `closed`; each status change writes a workflow
event that can be listed or exported for product handoff review. The readiness
rollup combines audit records, product backlog, promotion drafts, and lifecycle
events into a single score, maturity label, blockers, warnings, and next steps.
Promotion drafts, events, and readiness summaries contain product-planning
metadata only; they do not store raw debug bundles, raw API keys, private account
payloads, local build ids, or report contents. The review also rejects bundles
that appear to contain sensitive fields outside the privacy-safe support
boundary.

## First Use

1. Open `Welcome`.
2. Choose the player intent for this session.
3. Open `Connect`.
4. Paste a GW2 API key and save it.
5. Check key status.
6. Check permissions and review missing required or optional scopes.
7. Run connection diagnostic when the key appears stored but account-aware output is missing.
8. Queue account sync only after the permission grid is ready or you accept limited mode.
9. Drain one sync job in local development.
10. Export a debug bundle and run the support review harness if no expected result appears after diagnostic PASS.
11. Open `Freshness`.
12. Return to `Dashboard` and refresh status.

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
5. Use `Routes` when the next problem is achievement or collection execution. Start with `Load route sources`, then select a goal, enter available minutes, list completed step ids, list unlocked prerequisites such as `living_world_s3_access` and `achievement_api_access`, and decide whether to include group-content steps.
6. In `Routes`, use `Plan route` after confirming sources. Ready steps are grouped by map, blocked steps show missing prerequisites or group opt-in, and daily/weekly gates are marked as scheduling checks rather than guarantees. Export Markdown for a readable route plan or CSV for spreadsheet review.
7. Use `Build Fit` before converting gear. Synced official API character snapshots appear first when account sync has character detail; item and stat names are enriched from public `/v2/items` and `/v2/itemstats` metadata when available. Manual samples remain available as fallback.
8. In `Build Fit`, use `Preview upgrade pack`, `Import disabled rules`, `List upgrade rules`, and `Enable selected rule` when you want rune, sigil, and relic effect explanations to cite reviewed KB evidence. Re-run `Fit score` after enabling a rule.
9. Use `Freshness` before following account-aware or market-aware advice.
10. Use `Reports` to preview, unlock, retrieve artifacts, and reopen local report history.

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

## Achievement And Collection Routes

The Routes view turns route planning into a manual checklist:

- Source manifests: reviewed route step files loaded from `docs/knowledge_base/achievement_routes`.
- Goal: `aurora_sample`, `vision_sample`, `ad_infinitum_sample`, or all seeded sample goals.
- Available minutes: the session window used to fit ready steps.
- Completed step ids: skipped from the next plan.
- Unlocked prerequisite ids: player-provided facts that move steps from blocked to ready.
- Include group-content steps: opt-in before group/meta/fractal steps are considered ready.

Outputs separate ready, blocked, and time-gated steps. Every route export includes source ids, assumptions, and safety boundaries. The current reviewed seed is a planning scaffold backed by official API/source references, not a complete official achievement database.

Operator review gate:

- `Official achievement ids` lists the official ids to fetch for a draft preview.
- `Reviewer`, `Reviewed source id`, and `Review notes` are required context before reviewed promotion.
- `Fetch preview` calls the official fetch preview API and updates fetched/missing counts while keeping the source draft-only.
- `Promote reviewed` calls the reviewed gate and writes a planner-ingestible reviewed source manifest only after explicit reviewer confirmation.
- `Verify promoted plan` re-runs route planning and shows whether the promoted source id is present in the plan source ids.
- `Load audit` lists metadata-only promotion audit records filtered by reviewer.
- `Export audit CSV` exports the same audit metadata for operator review. It does not include raw API keys or private account payloads.
- `Release readiness` aggregates reviewed source manifests, promotion audit coverage, missing official achievement ids, and planner-ingestion status into a release gate.
- `Export readiness CSV` exports the readiness gate summary for handoff.
- `Source quality` scores reviewed sources and steps for evidence completeness, map inference risk, time-gate risk, and missing official ids.
- `Export quality CSV` exports step-level review flags and remediation suggestions.

Advanced operator flow:

- `POST /api/v1/achievement-routes/official-preview` accepts official `/v2/achievements` and `/v2/account/achievements` shaped payloads.
- The preview converts achievement details into draft route source candidates with inferred map hints, account progress status, source refs, and review warnings.
- `POST /api/v1/achievement-routes/official-fetch-preview` accepts achievement ids, batches public `/v2/achievements` through the gateway, merges safe account achievement progress summaries, and reports missing ids.
- `POST /api/v1/achievement-routes/official-fetch-preview/promote-reviewed` requires `confirmed_reviewed=true`, a reviewer name, and optional review notes before writing a reviewed route source manifest under `docs/knowledge_base/achievement_routes`.
- `GET /api/v1/achievement-routes/promotion-audit` lists reviewed promotion audit records and supports `format=markdown` or `format=csv`.
- `GET /api/v1/achievement-routes/release-readiness` summarizes reviewed source coverage, audit coverage, missing official ids, blockers, warnings, and next operator steps.
- `GET /api/v1/achievement-routes/source-quality` produces step-level source quality review with `format=markdown` and `format=csv`.
- Draft previews are not used by the route planner until this reviewed promotion gate writes a `source_status=reviewed` manifest.

## Freshness And Confidence

Dashboard, Freshness, preview reports, and full reports expose source confidence annotations. Treat stale account snapshots, manual market snapshots, old build sources, or unreviewed knowledge rules as manual-review signals.

## Build Upgrade Evidence

The Build Fit page can manage the `build_upgrade_effects` rule pack:

1. `Preview upgrade pack` shows reviewed candidate rules without persisting them.
2. `Import disabled rules` persists the reviewed candidates with `enabled=false`.
3. `List upgrade rules` refreshes persisted build upgrade rules.
4. `Enable selected rule` requires the backend reviewed-rule gate and records the reviewer name.
5. `Fit score` then uses only reviewed and enabled KB rules as evidence; disabled rules remain invisible to Build Fit explanations.

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
