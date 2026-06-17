# GW2Radar Senior Player User Guide

## 0. Read This First

This guide is written for experienced Guild Wars 2 players who want to use GW2Radar as a planning assistant, not as a general chatbot.

Current product status:

- Best suited for local demo, internal alpha, seed-user review, and manually reviewed reports.
- Strongest current value: legendary planning and account-specific planning reports.
- Build Fit is useful when you can provide structured build and gear data.
- Returner diagnosis is useful as a guided recovery workflow, but the dedicated Returner product flow is still an improvement priority.
- Market Radar is planning and observation support only. It does not trade, place orders, or promise profit.

GW2Radar does not:

- play the game for you;
- read client memory;
- automate trading;
- move items, buy items, craft items, or change gear;
- guarantee profit, meta correctness, DPS, or group acceptance.

It does:

- compare goals against account state;
- identify missing materials, currencies, achievements, and gear;
- preserve evidence and source attribution;
- generate manual action plans and reports.

## 1. Start The System

From the repository root:

```powershell
cd D:\Projects\gw2radar
python -m uvicorn gw2radar.api.main:app --app-dir src --host 127.0.0.1 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000/docs
```

Check health:

```http
GET /health
```

For local demo data:

```http
POST /mock/load
```

Use mock data when you want to test the flows without connecting a real GW2 account.

## 2. Connect Real Account Data

Use a GW2 API key only through the API key route. Do not paste keys into markdown files, source code, issue comments, logs, or screenshots.

Recommended GW2 API permissions for account planning:

- `account`
- `characters`
- `inventories`
- `wallet`
- `unlocks`
- `progression`

Connect and sync:

```http
PUT  /api/v1/account/api-key
POST /api/v1/account/sync
POST /api/v1/account/sync/drain-one
GET  /api/v1/account/sync/status
```

What this supports:

- owned materials;
- bank and inventory-derived planning state;
- wallet currencies;
- achievement and unlock progress;
- character/build recovery context.

What to check after sync:

```http
GET /goals
GET /api/v1/acquisition/final-maturity-rollup
```

If you are testing locally and account sync is not configured, use `/mock/load` first.

## 3. Opportunity A: Returner Account Diagnosis

Use this when your main question is:

> I have not played in a long time. What should I do first?

### Senior Player Mental Model

Returner diagnosis should answer:

- Am I missing major unlocks or progression systems?
- Should I recover mounts, masteries, story, maps, Wizard's Vault habits, or a build first?
- Am I ready for open world, strikes, fractals, WvW, or group play?
- Which advanced goals should I postpone?
- What should I do in the next 7 days?

### Current MVP Flow

The current implementation uses goal gap, action generation, evidence, and report generation:

```http
POST /mock/load
GET  /goals
GET  /goals/gw2:goal:aurora/gap
POST /goals/gw2:goal:aurora/actions/generate
POST /api/v1/reports/preview
```

Preview payload:

```json
{
  "goal_id": "gw2:goal:aurora",
  "report_type": "returner"
}
```

### How To Read The Result

Prioritize results in this order:

1. High urgency daily or weekly actions.
2. Missing account-bound or time-gated progress.
3. Evidence confidence notes.
4. Materials marked as reserved or do-not-sell.
5. Goals that look expensive or blocked.

### What Is Still Alpha

Dedicated Returner features still need deeper productization:

- Mount / mastery / expansion readiness.
- Skyscale, Griffon, Warclaw, and mobility priority.
- Wizard's Vault habit recovery.
- Fractal / strike / raid / WvW readiness checks.
- Playable character recommendation.
- 7-day and 30-day recovery plans.

Until those are implemented, treat Returner reports as a guided recovery preview, not a complete comeback coach.

## 4. Opportunity B: Legendary Goal Planning

Use this when your main question is:

> I want to craft a legendary. What am I missing, what should I do today, and what must I not sell?

This is the strongest current commercial flow.

### Best-Fit Use Cases

- Aurora / Vision / Conflux style long-term planning.
- Multiple legendary goals competing for the same materials.
- Mystic Clover, T6 materials, Ectoplasm, map currency, achievement, and collection bottlenecks.
- Daily and weekly route planning.
- Do-not-sell material reservation.

### Flow

1. Load demo graph or sync account.

```http
POST /mock/load
```

or:

```http
PUT  /api/v1/account/api-key
POST /api/v1/account/sync
POST /api/v1/account/sync/drain-one
```

2. Add or confirm a legendary goal.

```http
POST /api/v1/legendary/goals
```

Example:

```json
{
  "graph_goal_id": "gw2:goal:aurora",
  "priority": 100
}
```

3. Recompute the plan.

```http
GET  /api/v1/legendary/portfolio
POST /api/v1/legendary/recompute
GET  /api/v1/legendary/do-not-sell
```

4. Optional: add manual price snapshots for cost context.

```http
POST /api/v1/market/snapshots
POST /api/v1/market/watchlist
GET  /api/v1/market/goal-cost-index?goal_id=gw2:goal:aurora
GET  /api/v1/market/signals?goal_id=gw2:goal:aurora
```

5. Generate the Legendary Planner Pro report.

```http
POST /api/v1/legendary/report
GET  /api/v1/reports/jobs/{job_id}
```

### How To Read The Result

Focus on:

- shared material conflicts;
- time-gated requirements;
- daily route;
- weekly route;
- cheapest path;
- fastest path;
- do-not-sell list.

If an item appears in do-not-sell, interpret it as:

> This item supports an active goal. Do not sell it unless you manually decide that goal is no longer active.

It is not an automatic lock. GW2Radar does not change your inventory.

### Market Radar Add-On Interpretation

Market Radar helps answer:

- Is a missing item currently above or below recent manual snapshot average?
- Should I observe before buying?
- Which surplus items may be reviewed manually?

It must not be read as:

- guaranteed profit;
- buy now;
- automated trading;
- market manipulation.

## 5. Opportunity C: Build / Gear Transition Fit

Use this when your main question is:

> Can my account play this build now, what gear can I reuse, and how much will switching cost?

### Best-Fit Use Cases

- Choosing a low-friction open-world recovery build.
- Checking if an existing character can play a build now.
- Estimating conversion cost before committing gold.
- Comparing a premium build against a budget alternative.
- Reviewing whether a build is stale after patch changes.

### Build Data Requirements

Build Fit currently expects structured build data. Do not copy an entire third-party guide into the system.

A good build import includes:

- profession;
- specialization;
- role;
- game mode;
- patch version or freshness age;
- gear requirements by slot;
- rune, sigil, relic, and weapon requirements where known;
- source name, source URL, and attribution;
- estimated transition cost.

### Flow

1. Import a structured build.

```http
POST /api/v1/builds/import
```

2. List imported builds.

```http
GET /api/v1/builds
```

3. Evaluate fit against your account gear snapshot.

```http
POST /api/v1/builds/fit
```

4. Generate transition plan.

```http
POST /api/v1/builds/transition-plan
```

5. Generate Build Fit report.

```http
POST /api/v1/builds/report
GET  /api/v1/reports/jobs/{job_id}
```

### How To Read The Result

Use this order:

1. `playable_now`
2. `gear_match`
3. `unlock_match`
4. `cost_affordability`
5. `difficulty_match`
6. `preferred_mode_match`
7. `patch_freshness`
8. budget alternative

Senior player interpretation:

- High gear match + low transition cost: good recovery candidate.
- High cost + stale patch warning: review manually before committing.
- Low unlock match: build may be theoretically good but bad for this account now.
- Budget alternative: temporary planning suggestion, not a meta claim.

### What Is Still Alpha

Build Fit needs more source maturity before full commercial launch:

- reviewed build source registry;
- item stat normalization;
- ascended / exotic / legendary distinction;
- rune / sigil / relic completeness;
- weapon-set handling;
- patch-aware build freshness;
- game-mode-specific scoring.

## 6. Import External Knowledge And Evidence

Use this when you want reports to explain recommendations with reviewed knowledge.

### PDF / Source Import

```http
POST /api/v1/acquisition/local-pdf/import
POST /api/v1/acquisition/manual-note/import
POST /api/v1/acquisition/web-summary/import
```

### KB Review

```http
POST /api/v1/kb/load-directory
GET  /api/v1/kb/semantic-maturity
GET  /api/v1/kb/release-readiness
GET  /api/v1/kb/promotion-plan
```

### Evidence And Release Gates

```http
GET /api/v1/acquisition/evidence-coverage
GET /api/v1/acquisition/promotion-workflow
GET /api/v1/acquisition/promotion-action-plans
GET /api/v1/acquisition/promotion-release-manifest
GET /api/v1/acquisition/final-maturity-rollup
```

Do not promote source material into paid-report logic unless the source and KB review gates are acceptable.

## 7. What Senior Players Should Trust

Trust more:

- account-owned quantities;
- missing requirement math;
- do-not-sell reservations;
- explicit evidence refs;
- source-attributed build imports;
- manual transition cost estimates when inputs are accurate.

Trust less:

- stale build data;
- missing market history;
- unreviewed community summaries;
- any result based only on mock/demo graph;
- market trend signals with few snapshots.

## 8. Recommended Alpha Usage

Best current usage:

1. Use mock mode to understand the flow.
2. Use real account sync only in a trusted local environment.
3. Start with Legendary Planner Pro.
4. Use Build Fit for one or two manually structured builds.
5. Use Market snapshots only as planning context.
6. Generate reports for manual review.
7. Do not sell fully self-service paid access until production readiness gates are complete.

## 9. Quick Decision Table

| Your situation | Start here | Main result |
|---|---|---|
| Returning after a long break | Returner preview | What to do first and what to postpone |
| Working on Aurora or similar legendary | Legendary Planner Pro | Missing items, time gates, do-not-sell, routes |
| Unsure whether to switch builds | Build Fit Advisor | Fit score, missing gear, conversion cost |
| Wondering whether to buy now | Market add-on | Observe / hold / manually review signals |
| Preparing a paid report | Readiness gates | Evidence, KB, promotion, and safety status |

## 10. Production Readiness Caveat

GW2Radar is currently best described as a controlled MVP / internal alpha:

- useful for demos and seed-user reviewed reports;
- not yet positioned as a fully self-service commercial product;
- production launch should wait for stronger returner diagnosis, real account sync hardening, production secret storage, verified source gates, and player-facing UI.

The safest commercial path is:

1. Free returner preview.
2. Manually reviewed Legendary Planner Pro report.
3. Build Fit report for structured builds.
4. Market Radar as an add-on, not a standalone trading product.

