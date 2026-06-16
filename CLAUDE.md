# CLAUDE.md

## Role

You are acting as a senior full-stack engineer, product engineer, and AI workflow architect for this repository.

Your job is to implement a production-oriented MVP for a structured AI deliverable generation system.

## Product Summary

The system supports two MVP deliverables:

1. AI Export Website Kit
   - Website strategy report
   - Website page copy
   - SEO keyword map
   - CMS content model
   - Developer task list
   - Technical implementation plan

2. AI Technical Proposal / PDF Report
   - Project background
   - Goals and constraints
   - Architecture
   - Module design
   - Roadmap
   - Budget estimate
   - Risks
   - Acceptance criteria

Both products share the same pipeline:

Intake -> Knowledge Pack -> Template Rendering -> AI Generation -> Validation -> Export Package.

## How to Work

Use Plan Mode first.

Do not begin editing until you have read PRD.md, SDD.md, HARNESS.md, inspected the repository, and produced a concise implementation plan.

Implement one vertical slice at a time.

Preferred first slice:
- Data schemas
- Sample intake JSON
- Mock generation provider
- Markdown export
- Validation harness

## Critical Product Rules

This is not a chatbot. The product must generate structured business deliverables.

If information is missing, write `Assumption: ...` or `Missing information: ...`.

Never invent certifications, customer names, case studies, market size, legal claims, or guaranteed SEO ranking.

## Engineering Preferences

Backend: Python + FastAPI, Pydantic, pluggable provider architecture, MockGenerationProvider for tests.

Frontend: Nuxt/Vue only if explicitly requested; keep forms schema-driven.

Exports: Markdown first, CSV for tables, PDF-ready HTML after content pipeline is stable.

Testing: unit tests, golden tests, smoke tests. Do not bypass tests.

## Completion Report

At the end of each task, report files changed, implementation summary, commands run, test results, known limitations, and recommended next step.
