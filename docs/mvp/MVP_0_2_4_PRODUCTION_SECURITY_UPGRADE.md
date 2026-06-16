# MVP 0.2.4 Production Security Upgrade

Date: 2026-06-16

## Scope

This milestone implements P5 production security foundations for secret storage, deployment modes, audit-safe log sanitization, and private data deletion.

## Implemented

- `DeploymentMode`: `test`, `local_only`, `hosted_saas`.
- `SecretStore` protocol.
- `InMemorySecretStore` for test mode.
- `EncryptedLocalSecretStore` for local-only mode.
- `EncryptedDatabaseSecretStore` for hosted-compatible encrypted DB mode.
- `SecretModel` and Alembic migration `0006`.
- `EncryptedSecretPayload`.
- `encrypt_secret`, `decrypt_secret`, `fingerprint_api_key`.
- `sanitize_log_payload`.
- `delete_private_data`.
- Security API routes:

```http
POST   /api/v1/security/api-key
GET    /api/v1/security/api-key/status
DELETE /api/v1/security/api-key
DELETE /api/v1/security/private-data
```

## Security Rules

- Raw API keys are not stored in plaintext DB rows.
- Raw API keys are not returned by security routes.
- Key fingerprint is stable and non-reversible.
- Local and hosted modes require encrypted stores.
- Test mode may use in-memory storage.
- Private data deletion preserves public game graph data.

## Verification

Added tests:

- `tests/test_secret_store_interface.py`;
- `tests/test_encrypted_secret_stores.py`;
- `tests/test_secret_store_no_plaintext.py`;
- `tests/test_api_key_fingerprint.py`;
- `tests/test_log_sanitizer.py`;
- `tests/test_security_api_routes.py`;
- `tests/test_private_data_delete.py`;
- `tests/test_production_mode_requires_encryption.py`;
- `tests/test_constitution_compliance_security.py`.

Full verification:

```text
python -m pytest
python harness/run_smoke.py
python harness/run_sync_smoke.py
python -m alembic upgrade head
```

## Remaining Security Hardening

- Hosted SaaS still requires real tenant/user authentication before production.
- External KMS or OS vault integration remains future work.
- Current encrypted local/database stores use environment-derived Fernet keys.

## Next Milestone

P6 Returner Account Diagnosis:

- readiness score;
- missing unlock inference;
- 7-day and 30-day plans;
- returner report;
- evidence-labeled recommendations.
