# AGENTS.md

## Project Mission

This project builds two MVP products on one shared delivery-generation engine:

1. AI Export Website Kit Generator
2. AI Technical Proposal / PDF Report Generator

The product is not a general chatbot. It is a structured deliverable generator that collects user input, builds a project knowledge pack, renders domain templates, generates structured content, validates outputs, and exports PDF / Markdown / CSV / DOCX-ready files.

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
10. Keep the MVP simple: no multi-tenant SaaS, no complex billing portal, no template marketplace.

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
- Intake form schema
- Project workspace
- Knowledge pack builder
- Template renderer
- AI generation interface with mock provider
- Output validator
- Markdown export
- CSV export
- PDF-ready HTML export
- Sample data harness
- Admin preview page
- File package manifest

Out of scope for MVP:
- Full SaaS subscription system
- Team collaboration
- Multi-language dashboard
- Template marketplace
- Automatic website deployment
- WordPress/Webflow direct publishing
- Complex role-based enterprise admin
- Real payment integration unless explicitly requested

## Quality Gates

A task is not complete unless:
1. `pytest` or the project test command passes.
2. The generation smoke harness passes.
3. Sample Export Website Kit can be generated.
4. Sample Technical Proposal can be generated.
5. Required output sections are present.
6. Missing facts are marked as assumptions.
7. No fake certificates, fake customers, fake market data, or fake case studies are generated.
8. The output manifest matches the expected schema.

## Security and Safety

- Never store secrets in source code.
- Use environment variables for API keys.
- Validate user uploads by file type and size.
- Sanitize filenames.
- Do not execute uploaded files.
- Do not trust user-provided HTML.
- Keep generated documents separate from raw user uploads.
