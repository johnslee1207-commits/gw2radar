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

## Staged Validation Profiles

Use staged validation to avoid paying the full regression cost on every small
delivery slice:

```bash
python harness/run_stage_gate.py stage
python harness/run_stage_gate.py release
python harness/run_validation_profile.py fast
python harness/run_validation_profile.py smoke
python harness/run_validation_profile.py full
```

- `stage`: default stage gate for normal development; runs `fast` then `smoke`.
- `release`: milestone / release gate; runs `fast`, `smoke`, then `full`.
- `fast`: shared delivery lifecycle contract, productized report regression,
  player use-path semantic maturity audit, spec registry freshness, and partial
  spec reconciliation freshness, MVP closure readiness, and post-MVP roadmap
  freshness.
- `smoke`: MVP smoke, player UI E2E smoke, and account connection diagnostic.
- `full`: complete `pytest` regression.

Use `python harness/run_stage_gate.py --list` or
`python harness/run_validation_profile.py --list` to print the exact commands.

## Player UI E2E Smoke Command

```bash
python harness/run_player_ui_e2e_smoke.py
```

This smoke path verifies the player cockpit workflow without a browser: `/player`
loads, the demo graph is available, a sample Build Fit build can be imported,
the reviewed `build_upgrade_effects` rule pack can be imported disabled and
enabled through the review gate, Build Fit uses reviewed KB evidence, and a paid
Build Fit report artifact can be generated and retrieved.

## Achievement Route Smoke Command

```bash
python harness/run_achievement_route_smoke.py
```

This smoke path verifies the P1 Achievement & Collection Route Planner:
the `/player` UI exposes the route planner, `/api/v1/achievement-routes/plan`
returns deterministic ready/blocked/time-gated steps, and Markdown/CSV exports
preserve assumptions plus the manual-planning safety boundary.
It also verifies the P2 reviewed source ingestion layer:
`/api/v1/achievement-routes/sources` exposes reviewed route source manifests and
the generated plan cites the reviewed source id instead of relying only on the
built-in fallback seed.
It also verifies the P3 official achievement detail adapter:
official `/v2/achievements` and `/v2/account/achievements`-shaped payloads are
converted into draft route source candidates with account progress, source refs,
warnings, and Markdown export, without enabling them as reviewed guidance.
It also verifies the P4 official achievement fetch orchestration:
`/api/v1/achievement-routes/official-fetch-preview` batches `/v2/achievements`
ids through the gateway, merges safe account achievement progress summaries,
reports missing ids, and exports a draft-only preview.
It also verifies the P5 reviewed promotion gate:
`/api/v1/achievement-routes/official-fetch-preview/promote-reviewed` requires
explicit reviewer confirmation, writes a reviewed route source manifest, and
makes the promoted source eligible for route planner ingestion.
It also verifies the P6 operator review UI:
the `/player` Routes view exposes official achievement ids, reviewer, reviewed
source id, review notes, fetch preview, promote reviewed, and promoted-plan
verification controls.
It also verifies the P7 promotion audit trail:
reviewed promotions write metadata-only audit records and export JSON,
Markdown, and CSV without raw API keys or private account payloads.
It also verifies the P8 release readiness gate:
reviewed sources, promotion audit coverage, missing official achievement ids,
planner ingestion evidence, blockers, warnings, next steps, and CSV/Markdown
exports are aggregated into a release readiness summary.
It also verifies the P9 source quality review:
reviewed route sources and steps receive evidence completeness, map inference
risk, time-gate risk, missing-id remediation, score, Markdown, and CSV output.
It also verifies the P10 remediation queue:
source quality findings are converted into prioritized open reviewer tasks for
official id backfill, evidence backfill, map review, time-gate review, and CSV /
Markdown export.
It also verifies the P11 remediation review gate:
operators can mark remediation items acknowledged/resolved/deferred with manual
confirmation, reviewer notes, evidence refs, metadata-only audit listing, and
Markdown / CSV export.
It also verifies the P12 remediation readiness rollup:
queue items and review audit decisions are summarized into open P0/P1/P2 counts,
resolved/acknowledged/deferred counts, blockers, warnings, next steps, and a
go/no-go readiness export.
It also verifies the P13 operator action bundle:
source quality, remediation queue, remediation review action, review audit,
remediation readiness, and release readiness are combined into one front-end
workflow API with Markdown / CSV export.
It also verifies the P14 operator release packet:
the action bundle is packaged into deterministic Markdown, CSV, and manifest
exports with readiness scores, blockers, warnings, source paths, API refs, and
explicit safety boundaries.
It also verifies the P15 backfill candidate export:
unresolved remediation items become draft-only source edit candidates with
suggested fields, required review checks, evidence refs, Markdown export, and
CSV export without modifying source manifests.
It also verifies the P16 backfill candidate review gate:
operators can mark draft backfill candidates acknowledged/resolved/deferred with
manual confirmation, metadata-only audit records, Markdown / CSV audit exports,
and a readiness rollup before any separate source manifest edit or promotion.
It also verifies the P17 source edit patch draft:
resolved backfill candidates become deterministic source-edit patch draft
operations with current/proposed field context, Markdown / CSV export, and an
explicit no-auto-edit boundary.
It also verifies the P18 source edit patch apply gate:
operators can apply a source edit patch draft into a new draft source manifest
only after manual confirmation, with metadata-only audit export and no reviewed
planner ingestion.
It also verifies the P19 draft source promotion gate:
draft source manifests produced by patch apply can be promoted to reviewed
planner-ingestible manifests only after explicit reviewer confirmation, with
metadata-only audit export.
It also verifies the P20 unified release evidence bundle:
official promotion audit, source patch apply audit, draft source promotion
audit, source quality, release readiness, and operator release packet state are
combined into one read-only JSON/Markdown/CSV/manifest evidence bundle.
It also verifies the P21 release evidence archive gate:
the unified evidence bundle can be archived as immutable metadata with a
SHA-256 checksum, retention policy, archive index, and Markdown / CSV exports
without publishing content, editing source manifests, or storing secrets.
It also verifies the P22 release evidence archive diff review:
the latest two archived evidence records can be compared for checksum changes,
source/artifact/evidence-chain deltas, blocker/warning regressions,
improvements, next actions, and Markdown / CSV exports.
It also verifies the P23 release sign-off gate:
operators must explicitly confirm a metadata-only release sign-off after bundle,
archive, and diff review; sign-off records and audit exports include reviewer,
status, archive ids, diff ids, regressions, blockers, and safety boundaries.
It also verifies the P24 operator release dashboard:
bundle, archive, archive diff, and sign-off state are aggregated into one
read-only release dashboard with missing gates, blockers, warnings, next
actions, and Markdown / CSV exports.
It also verifies the P25 release export packet:
the dashboard, bundle, archive, diff, and sign-off audit schemas are packaged
into a final metadata-only release export packet with manifest, Markdown, and
CSV exports.
It also verifies the P26 release packet file export:
the release export packet can be written to deterministic local artifact files,
listed through an artifact index, and retrieved through a path-safe API.
It also verifies the P27 release packet bundle download:
the release export artifact files can be packaged into a local read-only zip
bundle with a manifest, checksum header, and whitelist validation.
It also verifies the P28 release packet verification import:
release export zip bundle bytes can be verified for checksum, schema, whitelist,
required files, and no-secret boundaries without executing or publishing files.
It also verifies the P29 release packet verification audit trail:
release export bundle verification results can be recorded as metadata-only
audit records and exported as Markdown / CSV without storing zip content.
It also verifies the P30 operator handoff checklist:
release packet, artifact files, zip bundle, verification, and verification audit
gates are summarized into one final metadata-only handoff readiness checklist.
It also verifies the P31-P34 release closure artifacts:
release notes, operator runbook, final release dashboard, and final code /
semantic maturity audit are generated as read-only metadata exports.

## Account Connection Diagnostic Command

```bash
python harness/run_account_connection_diagnostic.py
```

This diagnostic path verifies the player account connection chain with a fake
GW2 API gateway: pasted API key normalization, masked status, permission
inspection, account sync enqueue/status/drain-one, private-layer graph writes,
synced character snapshot exposure, Build Fit account-gear conversion, and raw
key non-leakage.

## Player Use Path Completeness Audit Command

```bash
python harness/run_player_use_path_audit.py
```

This audit path verifies the player-facing journey from `/player` shell through
account value diagnostics, Build Fit, Legendary Planner, Market Radar, and paid
report artifact metadata. It writes
`docs/ui/PLAYER_USE_PATH_COMPLETENESS_AUDIT.md` with an executable checklist,
semantic graph summary, known limits, and next priority. The audit is
summary-only and must not include raw API keys or private source payloads.

## Spec Registry Backlog Command

```bash
python harness/run_spec_registry.py
python harness/run_spec_registry.py --check
```

This harness scans tracked planning specs, MVP docs, tests, and the player
use-path maturity audit to generate
`docs/analysis/SPEC_REGISTRY_BACKLOG.md` and
`docs/analysis/SPEC_REGISTRY_BACKLOG.json`. The `--check` mode verifies the
registry is current and is part of the fast validation profile.

## Partial Spec Reconciliation Command

```bash
python harness/run_spec_reconciliation.py
python harness/run_spec_reconciliation.py --check
```

This harness reads `docs/analysis/SPEC_REGISTRY_BACKLOG.json`, extracts partial
specs, and writes `docs/analysis/PARTIAL_SPEC_RECONCILIATION.md` plus
`docs/analysis/PARTIAL_SPEC_RECONCILIATION.json`. It explains whether a partial
status is legacy spec drift, broad roadmap scope, MVP-out-of-scope live/provider
work, or a content-depth backlog. The `--check` mode is part of the fast
validation profile.

## MVP Closure Readiness Command

```bash
python harness/run_closure_readiness.py
python harness/run_closure_readiness.py --check
```

This harness reads the spec registry, partial spec reconciliation, and player
use-path audit outputs to determine whether any blocking MVP tasks remain. It
writes `docs/analysis/MVP_CLOSURE_READINESS.md` and
`docs/analysis/MVP_CLOSURE_READINESS.json`. The current closeout model treats
reviewed content depth, optional live API smoke documentation, and UI visual
polish as non-blocking post-MVP tracks.

## Post-MVP Production Roadmap Command

```bash
python harness/run_post_mvp_roadmap.py
python harness/run_post_mvp_roadmap.py --check
```

This harness reads the Trust/Credential, Production SaaS, and Master Planning
documents from `docs/analysis`, then writes
`docs/analysis/POST_MVP_PRODUCTION_ROADMAP.md` and
`docs/analysis/POST_MVP_PRODUCTION_ROADMAP.json`. It confirms the current MVP
remains closed, that Phase A Trust & Credential MVP and Phase B Report Product
Close Loop are implemented, and that Phase C Progression Decision Engine v1 is
the next recommended stage while SaaS, real billing, team workspace, and
autonomous agents remain later explicit stages.

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
promotion Markdown/CSV export, promotion status audit events, promotion
readiness rollup, and visible no-secret boundary copy.

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

## Achievement Route Harness Steps

1. Load `/player` and verify the Achievement Route Planner is present.
2. Confirm the Routes view exposes the operator review gate controls.
3. Submit a sample route request with known unlocked prerequisites.
4. Load reviewed route source manifests and confirm reviewed step count.
5. Confirm the route plan schema, ready steps, blocked steps, source id, and safety boundary.
6. Export Markdown and confirm assumptions are present with no guarantee wording.
7. Export CSV and confirm the deterministic route header is present.
8. Submit official achievement/account-achievement sample payloads.
9. Confirm generated route source candidates remain `draft`.
10. Export the official preview as Markdown and confirm review warnings are present.
11. Submit achievement ids to the official fetch preview endpoint.
12. Confirm fetched ids, missing ids, account progress, and draft-only status.
13. Export the fetch preview as Markdown and confirm review warnings are present.
14. Confirm promotion without reviewed confirmation is rejected.
15. Promote the fetch preview through the reviewed gate into a temporary source manifest.
16. Confirm the promotion audit lists the reviewer, source id, manifest path, and achievement id evidence.
17. Export the promotion audit as Markdown and CSV.
18. Load release readiness and confirm reviewed steps plus promotion audit coverage are counted.
19. Export release readiness as Markdown and CSV.
20. Load source quality and confirm missing official ids plus route review risks are flagged.
21. Export source quality as Markdown and CSV.
22. Load remediation queue and confirm missing official ids become P0 reviewer tasks.
23. Export remediation queue as Markdown and CSV.
24. Mark a remediation item reviewed and confirm metadata-only review audit.
25. Export remediation review audit as Markdown and CSV.
26. Load remediation readiness and confirm open P0/P1/P2 gate status.
27. Export remediation readiness as Markdown and CSV.
28. Load operator action bundle and confirm quality, queue, audit, and readiness are aggregated.
29. Record one remediation review through the action bundle.
30. Export operator action bundle as Markdown and CSV.
31. Load operator release packet and confirm manifest metadata.
32. Export operator release packet as Markdown, CSV, and manifest JSON.
33. Load backfill candidates and confirm unresolved remediation becomes draft edit suggestions.
34. Export backfill candidates as Markdown and CSV.
35. Mark one backfill candidate reviewed and confirm metadata-only audit output.
36. Export backfill candidate audit as Markdown and CSV.
37. Load backfill candidate readiness and confirm open candidate gate status.
38. Export backfill candidate readiness as Markdown and CSV.
39. Resolve one backfill candidate and confirm source edit patch draft operations are generated.
40. Export source edit patch draft as Markdown and CSV.
41. Apply one source edit patch draft into a draft source manifest after manual confirmation.
42. Export source edit patch apply audit as Markdown and CSV.
43. Promote one draft source manifest through the reviewed gate.
44. Export draft source promotion audit as Markdown and CSV.
45. Load unified release evidence bundle and confirm promotion, patch apply, quality, and readiness evidence are aggregated.
46. Export unified release evidence bundle as Markdown, CSV, and manifest JSON.
47. Archive the unified release evidence bundle and confirm reviewer, checksum, and retention metadata.
48. Export release evidence archive index as Markdown and CSV.
49. Compare the latest two release evidence archives and confirm checksum-only changes do not create regressions.
50. Export release evidence archive diff as Markdown and CSV.
51. Confirm unconfirmed release sign-off is rejected.
52. Record confirmed release sign-off and export sign-off audit as Markdown and CSV.
53. Load the operator release dashboard and confirm bundle, archive, diff, and sign-off state are summarized.
54. Export operator release dashboard as Markdown and CSV.
55. Load the release export packet and confirm artifact manifest metadata.
56. Export release export packet as Markdown, CSV, and manifest JSON.
57. Write release export packet artifact files and confirm artifact index metadata.
58. Retrieve one release export artifact through the path-safe API.
59. Load the release export bundle manifest and download the read-only zip bundle.
60. Verify the release export zip bundle bytes through the safe import verifier.
61. Record and export release bundle verification audit metadata.
62. Load and export the operator handoff checklist.
63. Load and export release notes.
64. Load and export the operator runbook.
65. Load and export the final release dashboard.
66. Load and export the final code / semantic maturity audit.
67. Confirm the route planner ingests the promoted reviewed source.

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
14. Update a promotion draft lifecycle status.
15. Export promotion status events as Markdown and CSV.
16. Load the support promotion readiness rollup and export it as Markdown and CSV.
17. Confirm the UI-facing contract returns a support status and finding.
18. Confirm the page tells reviewers not to request raw API keys or private account payloads.

## Required Checks

Export Website Kit must include Website Strategy Report, Website Page Copy, SEO Keyword Map, CMS Content Model, Developer Task List, Technical Implementation Plan.

Technical Proposal must include Background, Goals, Architecture, Modules, Roadmap, Budget, Risks, Acceptance Criteria.

## Prohibited Claims

Validator must flag fake certification claims, fake customer names, fake case studies, fake market size numbers, guaranteed Google ranking, and unsupported legal/compliance claims.
