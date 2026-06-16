# MVP 0.4.7 Patch Rule Confirmation Gate

## Scope

This milestone connects reviewed patch impact rule candidates to persistent `KnowledgeRule` records through an explicit confirmation gate.

Implemented:

- Persist reviewed patch rule candidates only after manual confirmation.
- Force persisted patch-derived rules to `enabled=false`.
- Skip duplicate persisted candidates by `(condition, action_type)`.
- Add a separate reviewed-rule enable gate.
- Expose the workflow through KB API endpoints.

## API

- `POST /api/v1/kb/patch-impact/{patch_id}/rule-candidates/persist`
  - Requires `{"confirmed": true}`.
  - Persists candidate rules with `enabled=false`.

- `POST /api/v1/kb/rules/{rule_id}/enable`
  - Requires `{"confirmed_reviewed": true}`.
  - Enables only reviewed KnowledgeRule records.

## Safety Boundary

- Candidate generation does not write to the database.
- Candidate persistence does not enable rules.
- Rule enablement is a separate action and rejects unreviewed rules.
- Duplicate persistence is idempotent and reports skipped candidates.

## Validation

- Service tests cover blocked persistence, disabled-by-default persistence, duplicate skipping, and enable gate behavior.
- API tests cover the same manual confirmation path.
