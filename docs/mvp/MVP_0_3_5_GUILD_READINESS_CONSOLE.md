# MVP 0.3.5 Guild / Static Readiness Console

Date: 2026-06-16

## Scope

This milestone implements P10 Guild / Static Readiness Console after individual-player monetization and payment abstraction.

## Implemented

- Guild model.
- Team model.
- Team member model.
- Consent record model.
- Team member invite with consent.
- Consent revocation.
- Role coverage inference.
- Team readiness score.
- Privacy-safe member summary.
- Guild readiness Markdown report.
- Versioned Guild / Team API routes:

```http
POST /api/v1/guilds
POST /api/v1/teams
POST /api/v1/teams/{team_id}/members/invite
POST /api/v1/teams/{team_id}/readiness
GET  /api/v1/teams/{team_id}/report
POST /api/v1/teams/{team_id}/members/{member_id}/revoke
```

## Privacy Boundaries

- Members must grant consent before readiness data affects team scoring.
- Consent revocation removes the member from readiness calculations.
- Reports show summary readiness only.
- Reports do not expose raw inventory, bank, API keys, or private account payloads.
- No gameplay automation or team command automation is implemented.

## Verification

Added tests:

- `tests/test_team_consent.py`;
- `tests/test_role_coverage.py`;
- `tests/test_team_readiness_score.py`;
- `tests/test_member_privacy_summary.py`;
- `tests/test_guild_report.py`;
- `tests/test_consent_revoke.py`;
- `tests/test_guild_api.py`.

Required verification:

```text
python -m pytest
python harness/run_smoke.py
python harness/run_sync_smoke.py
python -m alembic upgrade head
```

## Next Milestone

P11 Creator & Community Intelligence Console:

- community signal import;
- topic trends;
- question clusters;
- guide gap analysis;
- content opportunities;
- source attribution;
- no mass-copy policy;
- creator report.
