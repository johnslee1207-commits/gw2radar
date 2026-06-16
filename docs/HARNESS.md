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

## Required Checks

Export Website Kit must include Website Strategy Report, Website Page Copy, SEO Keyword Map, CMS Content Model, Developer Task List, Technical Implementation Plan.

Technical Proposal must include Background, Goals, Architecture, Modules, Roadmap, Budget, Risks, Acceptance Criteria.

## Prohibited Claims

Validator must flag fake certification claims, fake customer names, fake case studies, fake market size numbers, guaranteed Google ranking, and unsupported legal/compliance claims.
