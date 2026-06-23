# AGENTS.md

## Project Mission

This project builds GW2Radar: a local-first Guild Wars 2 player intelligence
tool for account connection diagnostics, legendary goal planning, build fit,
market/value insight, explainable knowledge-base rules, and privacy-safe support
handoff packets.

The product is not a general chatbot and does not automate gameplay, trading, or
external publishing. It is a deterministic, evidence-backed analysis and
delivery system that separates public game data, private player state, personal
intelligence, knowledge-base evidence, generated recommendations, and operator
handoff artifacts.

## Core Engineering Principles

1. Spec-driven development only.
2. Do not add features outside the current milestone.
3. Prefer small, verifiable changes.
4. Every implementation step must be covered by tests or a harness smoke check.
5. All generated content must preserve assumptions and avoid invented facts.
6. The system must separate user-provided facts from AI-generated recommendations.
7. Export files must be deterministic enough for validation.
8. Do not break existing tests to pass new ones.
9. Do not remove validation logic unless explicitly instructed.
10. Keep the MVP local-first and manual-review-first: no automated trading, no
    gameplay automation, no secret leakage, no guaranteed-return claims, and no
    external publishing unless explicitly requested.

## Required Workflow

Before editing code:
1. Read this file.
2. Read `/docs/PRD.md`.
3. Read `/docs/SDD.md`.
4. Read `/docs/HARNESS.md`.
5. Inspect the current repository structure.
6. Produce a short implementation plan.

During implementation:
1. Work in small slices.
2. Add or update tests for each slice.
3. Run the relevant test command.
4. Fix failures before moving on.

After implementation:
1. Summarize modified files.
2. Report test results.
3. Mention known limitations.
4. Suggest the next milestone.

## MVP Scope

In scope:
- GW2 API key lifecycle with encrypted local secret storage and masked status.
- Public game, private player state, and personal intelligence graph layers.
- Account sync queue, public refresh queue, diagnostics, and retry metadata.
- Legendary planner, Build Fit, Market Radar, account value, readiness, and
  player cockpit workflows.
- Knowledge-base source registry, reviewed rule packs, patch review flow, and
  explainable report artifacts.
- Productized commercial reports, support handoff packets, delivery lifecycle
  zip verification, metadata-only audits, and deterministic Markdown/CSV/JSON
  exports.
- Stage validation profiles and smoke harnesses.

Out of scope for MVP:
- Full SaaS subscription system
- Team collaboration
- Multi-language dashboard
- Template marketplace
- Automatic deployment or external publishing
- Complex role-based enterprise admin
- Real payment integration unless explicitly requested
- Automated GW2 trading, automatic gameplay actions, or profit guarantees

## Quality Gates

A task is not complete unless:
1. The relevant validation profile passes. Default stage gate:
   `python harness/run_stage_gate.py stage`.
2. Milestone or release closure also runs:
   `python harness/run_stage_gate.py release`.
3. Player use-path maturity audit remains ready with no failed checks.
4. Smoke harnesses preserve the mock legendary loop, player UI flow, and account
   connection diagnostic flow.
5. Required output sections and artifact manifests are present.
6. Missing or low-confidence facts are marked as assumptions, warnings, or
   review gates.
7. No raw API keys, raw debug bundles, private source payloads, fake market
   data, guaranteed-return claims, or automatic-trading instructions appear in
   generated outputs.
8. The output manifest, checksum, whitelist, and metadata-only audit schemas
   match their expected contracts.

## Security and Safety

- Never store secrets in source code.
- Use environment variables for API keys.
- Validate user uploads by file type and size.
- Sanitize filenames.
- Do not execute uploaded files.
- Do not trust user-provided HTML.
- Keep generated documents separate from raw user uploads.
- Keep private account data out of public knowledge-base content and public game
  data.
