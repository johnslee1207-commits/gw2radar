# Workspace Hygiene

## Purpose

GW2Radar keeps reviewed specifications, code, tests, and deterministic fixtures
in git. Local runtime outputs, raw source archives, generated report artifacts,
and operating-system metadata stay out of git unless a later milestone promotes a
specific summarized artifact into a reviewed document.

## Tracked Inputs

- `docs/analysis/*.md` stores planning, maturity, benchmark, and implementation
  briefs that explain why product stages exist.
- `docs/knowledge_base/**/*.md`, excluding `_sources`, stores reviewed or
  distilled knowledge-base content.
- `data/kb/*.csv` and `data/kb/*.jsonl` store compact evidence inventories, not
  raw PDF text.
- `tests/`, `harness/`, and `docs/HARNESS.md` store executable validation
  contracts.

## Ignored Local Outputs

- `desktop.ini` and `Thumbs.db` are local operating-system metadata.
- `*.db`, `*.sqlite`, `.test_tmp/`, and cache directories are local runtime
  state.
- `agent_execution_pack*.zip` is a transient handoff archive.
- `docs/knowledge_base/_sources/` contains raw downloaded source files such as
  PDFs and HTML captures. Reviewed summaries or source registries should be
  promoted into tracked Markdown/CSV/JSON files instead.
- `src/gw2radar/reports/artifacts/` contains generated local delivery artifacts.
  Tests should validate schemas, manifests, checksums, and path-safe retrieval
  instead of committing generated packet files.

## Promotion Rule

When a local output becomes product evidence, promote only the smallest reviewed
summary needed by the milestone. Do not commit raw API keys,
private account payloads, full-text PDF copies, generated zip contents, or debug
bundles.

## Review Checklist

1. `git status --short` should show only intentional source or documentation
   changes after ignored local outputs are produced.
2. New raw source directories must be listed in `.gitignore` before ingestion
   harnesses are run.
3. New generated artifact roots must be backed by deterministic tests and
   ignored unless explicitly promoted as reviewed metadata.
4. Planning specs copied into `docs/analysis/` should be committed when they are
   used to drive implementation priority.
