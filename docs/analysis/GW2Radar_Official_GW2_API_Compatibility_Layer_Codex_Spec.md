# GW2Radar Official GW2 API Compatibility Layer — Codex Development Spec

```text
Document ID: GW2RADAR_OFFICIAL_GW2_API_COMPATIBILITY_LAYER_CODEX_SPEC
Project: GW2Radar
Version: v0.1
Codename: Official GW2 API Compatibility Layer
Status: Draft for Codex Implementation
Primary Audience: Codex / Backend Developer / Architecture Reviewer
```

---

## 0. Purpose

This document defines the required implementation specification for the **Official GW2 API Compatibility Layer** in GW2Radar.

Current project status:

```text
API usage strategy: planned
API governance rules: planned
API gateway skeleton: required
Mock client: planned
Real official HTTP client: not yet confirmed
Official endpoint schema mapping: not yet complete
Token permission validation: must be added
Official API contract tests: must be added
```

Therefore, the correct project conclusion is:

> GW2Radar has not yet completed a real official GW2 API implementation.
> It currently has API planning and governance requirements, but still needs a formal official-compatible client, endpoint mapping, permission validation, batching, caching, rate limiting, evidence writing, and tests.

---

## 1. Design Goal

Implement a safe and official-document-aligned GW2 API access layer for GW2Radar.

The target architecture is:

```text
OfficialGw2ApiClient
+ Gw2ApiGateway
+ OfficialEndpointSchema
+ PermissionValidator
+ RateLimiter
+ CacheStore
+ EvidenceWriter
```

The implementation must ensure:

```text
1. All external GW2 API calls go through Gw2ApiGateway.
2. API keys are passed via Authorization header, not URL query.
3. API keys are never written to logs, evidence, reports, stack traces, or test snapshots.
4. /v2/tokeninfo is called to validate scopes before account-private analysis.
5. Public data uses cache and batching.
6. Private account data uses minimum required scopes.
7. 429 rate limit responses trigger backoff, not IP rotation.
8. Evidence metadata is written for every successful official API response.
9. Failed official responses do not pollute the graph.
10. Mock client and real client can coexist.
```

---

## 2. Constitutional Constraints

This implementation must comply with:

```text
GW2RADAR_PROJECT_CONSTITUTION.md
GW2RADAR_API_ACCESS_GOVERNANCE.md
docs/ontology/GW2_ONTOLOGY_CORE.md
docs/ontology/ACTION_SCHEMA.md
docs/mvp/MVP_0_1_CODEX_DEVELOPMENT_SPEC.md
```

Hard constraints:

```text
1. Do not implement gameplay automation.
2. Do not interact with the GW2 game client.
3. Do not read or modify game memory.
4. Do not implement automated trading.
5. Do not implement RMT, boosting, or account-sale features.
6. Do not implement proxy pools or IP rotation.
7. Do not bypass GW2 API rate limits.
8. Do not log API keys.
9. Do not store API keys in raw evidence.
10. Keep public game graph and private player graph separated.
```

---

## 3. Official API Alignment

GW2Radar must align with the official GW2 API v2 model.

Official API base URL:

```text
https://api.guildwars2.com
```

API version:

```text
v2
```

General endpoint pattern:

```text
https://api.guildwars2.com/v2/<endpoint>
```

Account-private endpoints require a player-generated API key.

The system must support:

```text
1. Public endpoints without API key.
2. Account-private endpoints with API key.
3. Token permission validation through /v2/tokeninfo.
4. ids= batch query pattern where supported.
5. lang parameter where useful.
6. Structured handling of 400 / 401 / 403 / 404 / 429 / 5xx.
```

---

## 4. Required Configuration

Add or validate configuration:

```yaml
gw2_api:
  base_url: "https://api.guildwars2.com"
  api_version: "v2"
  default_lang: "en"
  user_agent: "GW2Radar/<version> contact:<email-or-url>"
  timeout_seconds: 20
  retry_max_attempts: 3
  retry_backoff_base_seconds: 1
  retry_backoff_max_seconds: 60
```

Notes:

```text
1. The user_agent value should be configurable.
2. Do not include player API key in user agent.
3. Do not include player API key in URL query.
4. Use Authorization header for authenticated requests.
```

---

## 5. Authentication Rule

Preferred authentication method:

```http
Authorization: Bearer <API_KEY>
```

Forbidden by default:

```http
GET /v2/account?access_token=<API_KEY>
```

Reason:

```text
URL query parameters are more likely to be logged by proxies, servers, error trackers, or evidence writers.
```

Codex must implement a masking helper:

```text
mask_api_key(api_key: str) -> str
```

Example:

```text
ABCD...WXYZ
```

The full API key must never appear in:

```text
1. logs
2. exceptions
3. evidence source_url
4. raw payload
5. report output
6. pytest snapshots
```

---

## 6. Mandatory /v2/tokeninfo Permission Validation

### 6.1 Required Endpoint

Implement:

```http
GET /v2/tokeninfo
Authorization: Bearer <API_KEY>
```

The system must inspect returned scopes before performing account-private analysis.

### 6.2 Scope Validation Model

Create:

```text
PermissionValidator
```

Required methods:

```python
validate_for_legendary_goal(scopes: set[str]) -> PermissionValidationResult
validate_for_returner_diagnosis(scopes: set[str]) -> PermissionValidationResult
validate_for_build_fit(scopes: set[str]) -> PermissionValidationResult
```

### 6.3 MVP 0.1 Required Scopes

For Legendary Goal Intelligence:

```text
account
characters
inventories
wallet
progression
```

### 6.4 MVP 0.2 Required Scopes

For Returner Account Diagnosis:

```text
account
characters
inventories
wallet
progression
unlocks
```

### 6.5 MVP 0.3 Candidate Scopes

For Build Fit Graph:

```text
account
characters
inventories
builds
progression
unlocks
```

### 6.6 Missing Scope Behavior

If scopes are missing, return a structured error:

```json
{
  "error": "missing_api_key_scopes",
  "required_scopes": ["inventories", "wallet", "progression"],
  "granted_scopes": ["account", "characters"],
  "message": "Your GW2 API key is missing required permissions for this analysis."
}
```

Do not attempt partial analysis unless explicitly allowed by the feature.

---

## 7. Endpoint Implementation Priority

### 7.1 P0 — MVP 0.1 Required Endpoints

Implement these first:

```text
GET /v2/tokeninfo
GET /v2/account
GET /v2/characters
GET /v2/account/wallet
GET /v2/account/materials
GET /v2/account/bank
GET /v2/account/achievements
GET /v2/items?ids=...
GET /v2/achievements?ids=...
GET /v2/currencies?ids=...
GET /v2/commerce/prices?ids=...
```

### 7.2 P1 — MVP 0.2 Candidate Endpoints

Implement or verify official availability before coding:

```text
GET /v2/account/masteries
GET /v2/account/mounts/skins
GET /v2/account/skins
GET /v2/account/dyes
GET /v2/account/unlocks
```

Important Codex instruction:

```text
Before implementing each P1 endpoint, verify it exists in the official GW2 API v2 endpoint list.
Do not hardcode endpoints purely from memory.
```

### 7.3 P2 — MVP 0.3 Build Fit Candidate Endpoints

Implement or verify official availability before coding:

```text
GET /v2/characters/:id/equipment
GET /v2/characters/:id/specializations
GET /v2/characters/:id/buildtabs
GET /v2/characters/:id/equipmenttabs
GET /v2/professions
GET /v2/specializations
GET /v2/skills
GET /v2/traits
```

---

## 8. Batch Request Requirement

GW2 API v2 supports batch queries for many resource endpoints.

Forbidden pattern:

```python
for item_id in item_ids:
    client.get_item(item_id)
```

Required pattern:

```python
client.get_items(item_ids)
# internally calls:
# GET /v2/items?ids=1,2,3,...
```

Required batch client methods:

```python
get_items(ids: list[int], lang: str | None = None)
get_achievements(ids: list[int], lang: str | None = None)
get_currencies(ids: list[int], lang: str | None = None)
get_commerce_prices(ids: list[int])
```

Batching rules:

```text
1. Deduplicate ids before request.
2. Preserve caller-level mapping in response.
3. Split into chunks if official endpoint or URL length requires it.
4. Cache batch responses by endpoint + sorted ids + lang.
5. Never loop one HTTP call per id unless no batch endpoint exists.
```

---

## 9. Rate Limit and Retry Behavior

### 9.1 Default Local Rate Limit

Use conservative internal limits:

```yaml
gw2_api_rate_limit:
  scope: outbound_ip
  burst_capacity: 250
  refill_rate_per_second: 4
  hard_max_per_minute: 240
```

### 9.2 429 Handling

On HTTP 429:

```text
1. Do not switch IP.
2. Do not use proxy fallback.
3. Record sanitized request metadata.
4. Apply exponential backoff.
5. Temporarily reduce request rate.
6. Keep task in delayed queue.
7. Return refresh_pending or rate_limited_retrying to API caller.
```

### 9.3 Retryable Status Codes

Retry with backoff:

```text
429
500
502
503
504
network timeout
connection reset
```

Do not retry blindly:

```text
400
401
403
404
```

---

## 10. Error Handling Contract

Implement structured errors.

### 10.1 401 Invalid Token

```json
{
  "error": "invalid_api_key",
  "message": "The provided GW2 API key is invalid or expired."
}
```

### 10.2 403 Missing Permission

```json
{
  "error": "missing_permission",
  "message": "The API key does not grant access to this resource.",
  "required_scope": "inventories"
}
```

### 10.3 404 Resource Not Found

```json
{
  "error": "resource_not_found",
  "endpoint": "/v2/items",
  "resource_id": 12345
}
```

### 10.4 429 Rate Limited

```json
{
  "error": "rate_limited_retrying",
  "message": "GW2 API rate limit reached. Refresh has been delayed and will retry automatically."
}
```

### 10.5 5xx API Temporary Failure

```json
{
  "error": "gw2_api_temporary_failure",
  "message": "GW2 API is temporarily unavailable. Please retry later."
}
```

---

## 11. Cache Requirements

### 11.1 Endpoint TTL Defaults

```yaml
endpoint_ttl:
  items: 72h
  recipes: 72h
  achievements: 72h
  currencies: 72h
  professions: 72h
  specializations: 72h
  skills: 72h
  traits: 72h
  account: 30m
  characters: 30m
  wallet: 30m
  materials: 30m
  bank: 30m
  account_achievements: 60m
  commerce_prices_goal_items: 30m
  commerce_listings: 60m
```

### 11.2 Cache Key

Cache key must include:

```text
endpoint
method
sanitized params
lang
authenticated/public flag
account id or token hash for private endpoints
```

Do not use the raw API key as cache key.

Use a secure hash if token identity is needed:

```text
sha256(api_key + server_secret)
```

### 11.3 Cache Metadata

Each cached response must store:

```yaml
CacheRecord:
  cache_key: string
  endpoint: string
  params_hash: string
  fetched_at: datetime
  expires_at: datetime
  status_code: int
  response_hash: string
  source_url_sanitized: string
```

---

## 12. Evidence Writing Requirements

Every successful official API response used to create graph facts must produce evidence metadata.

### 12.1 Evidence Schema

```yaml
Evidence:
  evidence_id: string
  source_type: gw2_api
  source_url: string
  endpoint: string
  request_params_hash: string
  fetched_at: datetime
  response_hash: string
  status_code: int
  cache_hit: bool
  confidence: 1.0
```

### 12.2 Sanitization Rules

Evidence must not include:

```text
1. API key
2. Authorization header
3. access_token
4. raw private account payload unless stored in private player state storage
5. full request URL containing secrets
```

### 12.3 Public vs Private Evidence

Public evidence may be linked to Public Game Graph.

Private account evidence must remain linked only to Private Player State Graph or Personal Intelligence Graph.

Forbidden:

```text
Private account evidence → Public Game Graph
```

---

## 13. Recommended Module Layout

Create or update:

```text
src/gw2radar/ingest/
├── official_gw2_api_client.py
├── gw2_api_gateway.py
├── endpoint_schema.py
├── permission_validator.py
├── rate_limiter.py
├── cache_store.py
├── request_queue.py
├── evidence_writer.py
└── errors.py
```

Tests:

```text
tests/test_gw2_api_client_official_contract.py
tests/test_gw2_api_permissions.py
tests/test_gw2_api_batching.py
tests/test_gw2_api_rate_limit_behavior.py
tests/test_gw2_api_key_safety.py
tests/test_gw2_api_evidence_sanitization.py
```

---

## 14. Official Client Interface

Implement an interface similar to:

```python
class OfficialGw2ApiClient:
    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        timeout_seconds: int = 20,
        user_agent: str | None = None,
    ) -> None:
        ...

    def tokeninfo(self) -> dict:
        ...

    def account(self) -> dict:
        ...

    def characters(self) -> list[dict]:
        ...

    def account_wallet(self) -> list[dict]:
        ...

    def account_materials(self) -> list[dict]:
        ...

    def account_bank(self) -> list[dict]:
        ...

    def account_achievements(self) -> list[dict]:
        ...

    def items(self, ids: list[int], lang: str | None = None) -> list[dict]:
        ...

    def achievements(self, ids: list[int], lang: str | None = None) -> list[dict]:
        ...

    def currencies(self, ids: list[int], lang: str | None = None) -> list[dict]:
        ...

    def commerce_prices(self, ids: list[int]) -> list[dict]:
        ...
```

---

## 15. Gateway Responsibilities

`Gw2ApiGateway` must be the only public entry point for external API access.

Responsibilities:

```text
1. Validate API key scopes through tokeninfo.
2. Check cache before official call.
3. Enforce rate limit.
4. Enqueue or delay requests when needed.
5. Call OfficialGw2ApiClient.
6. Handle errors.
7. Write evidence.
8. Return normalized response to ingestion modules.
```

Feature modules must call:

```text
Gw2ApiGateway
```

not:

```text
OfficialGw2ApiClient directly
```

---

## 16. Mock and Real Client Coexistence

MVP development must preserve mock behavior.

Required modes:

```yaml
gw2_api_mode:
  mode: mock | real
```

Rules:

```text
1. Unit tests should default to mock.
2. Official contract tests may use mocked HTTP responses.
3. No test should require a real player API key by default.
4. Real API integration tests must be explicitly opt-in.
5. Real API keys must be loaded only from environment variables.
```

Example:

```text
GW2RADAR_ENABLE_REAL_GW2_API_TESTS=1
GW2RADAR_TEST_API_KEY=<key>
```

Never commit real API keys.

---

## 17. Contract Tests

### 17.1 Official Base URL Test

```text
Assert default base_url == https://api.guildwars2.com
```

### 17.2 Auth Header Test

```text
Authenticated requests must send Authorization: Bearer <masked>
Request URL must not contain access_token.
```

### 17.3 Tokeninfo Scope Test

```text
Given tokeninfo returns scopes missing inventories,
validate_for_legendary_goal must fail with missing_api_key_scopes.
```

### 17.4 Batching Test

```text
Given item ids [1, 2, 3],
client must issue one /v2/items?ids=1,2,3 request,
not three individual requests.
```

### 17.5 Rate Limit Test

```text
Given HTTP 429,
gateway returns rate_limited_retrying,
does not switch IP,
does not call proxy fallback.
```

### 17.6 Evidence Sanitization Test

```text
Evidence source_url must not contain API key.
Evidence raw payload must not contain Authorization header.
Evidence must include endpoint, fetched_at, response_hash, status_code.
```

### 17.7 API Key Safety Test

```text
Logs, errors, reports, and evidence must not contain the full API key.
```

---

## 18. FastAPI Diagnostic Endpoints

Optional but recommended for internal development.

### 18.1 API Key Scope Check

```http
POST /api/v1/gw2/tokeninfo/check
```

Request:

```json
{
  "api_key": "redacted-or-submitted-securely",
  "feature": "legendary_goal"
}
```

Response:

```json
{
  "valid": true,
  "granted_scopes": ["account", "characters", "inventories", "wallet", "progression"],
  "missing_scopes": []
}
```

### 18.2 API Gateway Health

```http
GET /api/v1/gw2/gateway/health
```

Response:

```json
{
  "mode": "mock",
  "rate_limiter": "enabled",
  "cache": "enabled",
  "queue": "enabled"
}
```

---

## 19. MVP 0.1 Acceptance Criteria Addendum

MVP 0.1 is not API-complete until this layer passes:

```text
Functional:
- [ ] OfficialGw2ApiClient exists.
- [ ] Gw2ApiGateway exists.
- [ ] /v2/tokeninfo is implemented.
- [ ] PermissionValidator exists.
- [ ] P0 endpoints are implemented or stubbed with contract tests.
- [ ] Batch ids requests are implemented for items, achievements, currencies, prices.
- [ ] Mock and real modes coexist.

Security:
- [ ] API key uses Authorization header.
- [ ] API key is not placed in URL query.
- [ ] API key is masked in logs.
- [ ] API key is excluded from evidence.
- [ ] API key is excluded from reports.

Governance:
- [ ] No proxy pool.
- [ ] No IP rotation.
- [ ] 429 triggers backoff, not IP switching.
- [ ] All external API calls go through Gw2ApiGateway.

Evidence:
- [ ] Official API responses write sanitized evidence metadata.
- [ ] Private account evidence is not linked to Public Game Graph.
- [ ] Failed responses do not create graph facts.

Tests:
- [ ] Official contract tests pass.
- [ ] Permission tests pass.
- [ ] Batching tests pass.
- [ ] Rate limit behavior tests pass.
- [ ] API key safety tests pass.
- [ ] Evidence sanitization tests pass.
```

---

## 20. Codex Implementation Prompt

Use this prompt directly.

```text
Current project: GW2Radar

Implement the Official GW2 API Compatibility Layer.

Before coding, read and comply with:
1. GW2RADAR_PROJECT_CONSTITUTION.md
2. GW2RADAR_API_ACCESS_GOVERNANCE.md
3. docs/ontology/GW2_ONTOLOGY_CORE.md
4. docs/ontology/ACTION_SCHEMA.md
5. docs/mvp/MVP_0_1_CODEX_DEVELOPMENT_SPEC.md

Hard constraints:
- Do not implement gameplay automation.
- Do not interact with the GW2 game client.
- Do not read or modify game memory.
- Do not implement automated trading.
- Do not implement RMT, boosting, or account-sale features.
- Do not implement proxy pools or IP rotation.
- Do not bypass GW2 API rate limits.
- Do not log API keys.
- Do not store API keys in raw evidence.
- Keep public game graph and private player graph separated.

Implement:
1. src/gw2radar/ingest/official_gw2_api_client.py
2. src/gw2radar/ingest/gw2_api_gateway.py
3. src/gw2radar/ingest/endpoint_schema.py
4. src/gw2radar/ingest/permission_validator.py
5. src/gw2radar/ingest/rate_limiter.py
6. src/gw2radar/ingest/cache_store.py
7. src/gw2radar/ingest/evidence_writer.py
8. src/gw2radar/ingest/errors.py

Required behavior:
- Use base URL https://api.guildwars2.com.
- Use API version v2.
- Use Authorization: Bearer <API_KEY>.
- Do not pass API key in URL.
- Implement /v2/tokeninfo.
- Validate scopes for legendary_goal, returner_diagnosis, and build_fit.
- Implement P0 endpoints.
- Implement ids batching for items, achievements, currencies, commerce prices.
- Implement structured errors.
- Implement 429 backoff path.
- Write sanitized evidence metadata.
- Preserve mock mode and real mode.

Add tests:
- test_gw2_api_client_official_contract.py
- test_gw2_api_permissions.py
- test_gw2_api_batching.py
- test_gw2_api_rate_limit_behavior.py
- test_gw2_api_key_safety.py
- test_gw2_api_evidence_sanitization.py

Acceptance:
- pytest passes.
- No API key appears in logs, evidence, reports, or URLs.
- No proxy pool or IP rotation exists.
- All external calls go through Gw2ApiGateway.
- Failed official responses do not pollute graph facts.
```

---

## 21. Development Order

Recommended implementation order:

```text
1. Add errors.py.
2. Add endpoint_schema.py.
3. Add official_gw2_api_client.py with mocked HTTP tests.
4. Add permission_validator.py.
5. Add rate_limiter.py.
6. Add cache_store.py.
7. Add evidence_writer.py.
8. Add gw2_api_gateway.py.
9. Add contract tests.
10. Add FastAPI diagnostic endpoints.
11. Run full pytest.
```

---

## 22. Final Conclusion

Current GW2Radar API state:

```text
Official API strategy: planned
Official API governance: planned
Official API real implementation: not complete
```

Required next milestone:

```text
GW2Radar MVP 0.1 Official GW2 API Compatibility Layer
```

Completion means:

```text
The project can safely and correctly access official GW2 API v2 through a governed gateway,
validate token scopes,
batch public resource requests,
cache responses,
respect rate limits,
write sanitized evidence,
and keep private account data isolated.
```
