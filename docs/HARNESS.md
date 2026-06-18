# Harness Engineering Guide

## Purpose

The harness verifies the MVP generation pipeline without calling real AI APIs.

## Required Sample Inputs

1. harness/sample_export_website_intake.json
2. harness/sample_technical_proposal_intake.json

## Required Smoke Command

```bash
python harness/run_smoke.py
```

## Player UI E2E Smoke Command

```bash
python harness/run_player_ui_e2e_smoke.py
```

This smoke path verifies the player cockpit workflow without a browser: `/player`
loads, the demo graph is available, a sample Build Fit build can be imported,
the reviewed `build_upgrade_effects` rule pack can be imported disabled and
enabled through the review gate, Build Fit uses reviewed KB evidence, and a paid
Build Fit report artifact can be generated and retrieved.

## Account Connection Diagnostic Command

```bash
python harness/run_account_connection_diagnostic.py
```

This diagnostic path verifies the player account connection chain with a fake
GW2 API gateway: pasted API key normalization, masked status, permission
inspection, account sync enqueue/status/drain-one, private-layer graph writes,
synced character snapshot exposure, Build Fit account-gear conversion, and raw
key non-leakage.

## Account Debug Bundle Review Command

```bash
python harness/run_account_debug_bundle_review.py
```

Without arguments, this harness verifies the local support parser for privacy-safe
debug bundles. It detects missing permissions, delayed sync, incomplete player UI
flow after a ready backend, privacy-boundary violations, and a fully ready flow.

To review a player-exported bundle:

```bash
python harness/run_account_debug_bundle_review.py path/to/account_debug_bundle.json
```

The review output is Markdown and must not contain raw API keys, private account
payloads, local build ids, or report artifact contents.

## Support Review UI Smoke Command

```bash
python harness/run_support_review_ui_smoke.py
```

This smoke path verifies the `/support` operator page, static support script,
support-specific styles, the review API contract, safe audit write/list behavior,
audit filtering, privacy-safe CSV export, metrics summary, remediation playbook,
product fix backlog, backlog Markdown/CSV export, roadmap draft promotion,
promotion Markdown/CSV export, and visible no-secret boundary copy.

## Smoke Harness Steps

1. Load sample intake JSON.
2. Validate intake schema.
3. Build a knowledge pack.
4. Render selected template.
5. Use MockGenerationProvider.
6. Generate output sections.
7. Validate required sections.
8. Export Markdown and CSV files.
9. Create package manifest.
10. Print PASS/FAIL.
11. Exit with non-zero status on failure.

## Player UI E2E Harness Steps

1. Load `/player` and verify the cockpit shell is present.
2. Load the demo graph.
3. Import a structured Power Quickness Herald build.
4. Preview and import `build_upgrade_effects` rules with `enabled=false`.
5. Enable one reviewed build upgrade rule through the explicit review gate.
6. Run Build Fit against matching account gear.
7. Assert upgrade-effect evidence comes from a reviewed enabled KB rule.
8. Grant the local Build Fit report entitlement.
9. Generate a Markdown Build Fit report.
10. Retrieve the generated artifact and verify Build Fit sections are present.
11. Print PASS/FAIL and exit non-zero on failure.

## Account Connection Diagnostic Steps

1. Store a pasted API key containing whitespace and a zero-width character.
2. Confirm only the masked key is returned.
3. Inspect token permissions using the normalized stored key.
4. Queue account sync and inspect endpoint-level queued progress.
5. Drain one account sync job.
6. Confirm private player-state entities and endpoint success are visible.
7. Confirm synced official character snapshots precede manual samples.
8. Convert the synced character snapshot into Build Fit account gear.
9. Confirm armor, weapon, rune, and sigil categories are present.
10. Confirm the raw API key never appears in responses.

## Account Debug Bundle Review Steps

1. Load a privacy-safe account debug bundle JSON file.
2. Validate the bundle schema.
3. Check for sensitive field names that violate the support boundary.
4. Classify missing key, missing permissions, delayed sync, missing queue, missing private snapshot, missing character snapshot, Build Fit snapshot-load gaps, or incomplete UI flow.
5. Render a Markdown support review with evidence paths and recommended actions.
6. Exit non-zero only when the bundle cannot be read or the deterministic harness checks fail.

## Support Review UI Steps

1. Serve `/support`.
2. Serve `/player-ui/support.js` and shared styles.
3. Submit a privacy-safe sample bundle to `/account/debug-bundle/review`.
4. Save an audit record through `/account/debug-bundle/review/audit`.
5. List recent audit records and confirm at least one safe metadata record exists.
6. Filter audit records by severity and reviewer.
7. Export a privacy-safe CSV audit view.
8. Load metrics summary for total cases, status counts, severity counts, and top blockers.
9. Load remediation playbook entries for mapped blockers.
10. Load product fix backlog items ranked from playbook signals.
11. Export the product fix backlog as Markdown and CSV.
12. Promote a backlog item into a draft roadmap/issue artifact.
13. Export promotion drafts as Markdown and CSV.
14. Confirm the UI-facing contract returns a support status and finding.
15. Confirm the page tells reviewers not to request raw API keys or private account payloads.

## Required Checks

Export Website Kit must include Website Strategy Report, Website Page Copy, SEO Keyword Map, CMS Content Model, Developer Task List, Technical Implementation Plan.

Technical Proposal must include Background, Goals, Architecture, Modules, Roadmap, Budget, Risks, Acceptance Criteria.

## Prohibited Claims

Validator must flag fake certification claims, fake customer names, fake case studies, fake market size numbers, guaranteed Google ranking, and unsupported legal/compliance claims.
