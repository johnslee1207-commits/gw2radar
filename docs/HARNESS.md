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

## Required Checks

Export Website Kit must include Website Strategy Report, Website Page Copy, SEO Keyword Map, CMS Content Model, Developer Task List, Technical Implementation Plan.

Technical Proposal must include Background, Goals, Architecture, Modules, Roadmap, Budget, Risks, Acceptance Criteria.

## Prohibited Claims

Validator must flag fake certification claims, fake customer names, fake case studies, fake market size numbers, guaranteed Google ranking, and unsupported legal/compliance claims.
