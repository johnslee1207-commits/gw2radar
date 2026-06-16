# MVP 0.4.1 KB-backed Recommendation Explanations

Date: 2026-06-16

## Scope

P5 connects reviewed Knowledge Base rules to recommendation and report explanations without changing core inference.

Implemented deliverables:

- KB explanation service for actions;
- reviewed/enabled rule matching by action type and optional linked entity condition;
- KB-backed Markdown report variant;
- KB action explanation API endpoint;
- KB-backed report API endpoint.

## API Surface

- `GET /api/v1/kb/goals/{goal_id}/action-explanations`
- `GET /reports/{goal_id}/markdown/kb`

## Matching Contract

KB explanations are applied only when:

- `KnowledgeRule.enabled = true`;
- `KnowledgeRule.review_status = reviewed`;
- `KnowledgeRule.action_type` matches the generated action type;
- if the rule condition contains `article_links_any_entity:*`, the action target entity must be included.

This keeps KB explanations conservative and prevents unreviewed or loosely related content from affecting recommendations.

## Report Behavior

The original Markdown report remains unchanged.

The KB-backed report appends:

- `Knowledge Base Explanations`;
- KB rule name;
- matched action id;
- reviewed recommendation;
- explanation template;
- KB confidence and source refs;
- explicit KB boundary notes.

## Safety Boundaries

- KB explanations do not mutate action priority.
- KB explanations do not automate gameplay.
- KB explanations do not replace manual player decisions.
- Draft, deprecated, disabled, or unreviewed rules are ignored.

## Verification

Targeted tests:

- `tests/test_kb_explanation.py`
- `tests/test_kb_backed_report.py`
- `tests/test_kb_explanation_api.py`

Result: P5 targeted tests passed.

## Known Limitations

- KB rules do not yet alter ranking or action generation.
- Matching is deterministic string/schema matching, not semantic retrieval.
- KB-backed commercial artifacts are not yet generated through the paid report engine.

## Next Priority

P6: KB-backed Paid Report Artifact Integration.
