# Product Requirements Document

## Product Direction

GW2Radar is a local-first Guild Wars 2 player intelligence product. It helps
experienced players understand account readiness, legendary goals, build fit,
market/value context, knowledge-base evidence, and support handoff state without
automating gameplay or trading.

## Shared Promise

Collect public GW2 data, private player account summaries, reviewed knowledge
sources, and deterministic planner outputs into explainable recommendations,
reports, dashboards, and operator handoff packets.

The system must preserve source boundaries:

- Public game data belongs in the public graph and KB layers.
- Private account data belongs in encrypted/local private or personal layers.
- Generated recommendations must cite assumptions, warnings, evidence refs, and
  manual-action boundaries.
- Delivery artifacts must be deterministic, checksumed, zip-verified, and
  metadata-audited.

## Core Player Workflows

- Connect a GW2 API key, inspect permissions, and understand missing/blocked
  account-aware results.
- Sync private account summaries through queue-backed, retry-aware workers.
- Review account value, source diagnostics, and privacy-safe history deltas.
- Plan legendary goals with shared requirements, cheap/fast paths, and
  do-not-sell guidance.
- Evaluate Build Fit and gear transition cost with account value evidence.
- Review Market Radar signals, watchlists, goal cost index, and hold/sell
  candidates with no-trading guarantees.
- Use Player UI readiness, history correlation, support handoff, and session
  packet workflows.

## Knowledge And Commercial Workflows

- Maintain reviewed KB sources, source semantics, rule packs, patch review, and
  release readiness evidence.
- Generate productized reports for account value, legendary gap, and build
  readiness.
- Package support and commercial artifacts through the shared delivery lifecycle
  framework with whitelist zip verification and metadata-only audits.
- Expose deterministic Markdown, CSV, JSON, and HTML-ready artifacts.

## MVP Boundary

In scope:

- Local-first API, SQLite persistence, deterministic mock data, and fake gateway
  tests.
- Encrypted secret storage and masked API key status.
- Public/private/personal graph layering.
- Account/public/market refresh queues with worker health and retry metadata.
- Player cockpit, readiness summaries, history, and support handoff flows.
- KB-backed explanations and reviewed rule lifecycle.
- Commercial productized reports and delivery artifacts.
- Stage validation gates: `stage` for normal work and `release` for milestone
  closure.

Out of scope unless explicitly requested:

- Multi-tenant SaaS operations.
- Real payment provider integration.
- Team collaboration beyond modeled guild/static readiness.
- Automatic external publishing or website deployment.
- Automated trading, automatic gameplay actions, profit guarantees, or live-state
  certification.

## Quality Expectations

- The default development gate is `python harness/run_stage_gate.py stage`.
- Release or milestone closure uses `python harness/run_stage_gate.py release`.
- Use-path maturity audit should remain ready with no failed checks.
- Generated artifacts must exclude raw keys, raw debug bundles, private source
  payloads, executable content, and unsupported claims.
- All recommendations must preserve assumptions and manual-review boundaries.
