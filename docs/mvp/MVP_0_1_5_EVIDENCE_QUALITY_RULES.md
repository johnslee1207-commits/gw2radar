# MVP 0.1.5 Evidence Freshness and Confidence Rules

MVP 0.1.5 makes evidence quality visible to action generation and reports.

## Rules

- Strong recommendations require evidence confidence of at least `0.75`.
- Non-mock evidence older than 7 days is treated as stale by default.
- Mock evidence has a long stale window for deterministic MVP testing.
- Missing evidence is treated as stale and low-confidence.

## Action Effects

If an action is backed by stale or low-confidence evidence:

- priority is capped at `0.55`;
- urgency is downgraded to `low`;
- reason codes include `stale_evidence` and/or `low_confidence_evidence`;
- explanation tells the player to verify before acting.

Actions remain recommendation-only.

## Report Effects

Markdown reports now include evidence quality notes:

- confidence label;
- minimum confidence;
- stale evidence flag;
- evidence source ids, source type, and confidence.

## Verification

Covered by:

- `tests/test_evidence_quality.py`
- `tests/test_action_generator.py`
- `tests/test_markdown_report.py`
