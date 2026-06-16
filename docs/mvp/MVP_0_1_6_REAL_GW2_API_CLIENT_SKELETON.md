# MVP 0.1.6 Real GW2 API Client Skeleton

MVP 0.1.6 adds a conservative official GW2 API HTTP client skeleton.

## Implemented

- Standard-library HTTP client based on `urllib`.
- Configurable `GW2RADAR_API_BASE_URL`.
- Optional `GW2RADAR_API_KEY` for local development.
- API key is placed in the `Authorization` header only.
- API key is not included in query strings.
- API key is not included in exception messages.
- HTTP 429 maps to `Gw2ApiRateLimitError`.
- Non-429 HTTP errors map to `Gw2ApiClientError`.
- Tests use fake transport and do not contact the public internet.

## Still Required Through Gateway

All business access must continue to use:

```text
Feature -> Gw2ApiGateway -> GW2ApiClient
```

The client does not implement:

- proxy pools;
- IP rotation;
- retry loops;
- high-frequency scraping;
- automated trading;
- gameplay automation.

Cache, rate limits, queueing, and backoff remain the responsibility of `Gw2ApiGateway`.

## Verification

Covered by:

- `tests/test_gw2_api_client.py`
- `tests/test_api_governance.py`
- `tests/test_gateway_contract.py`
