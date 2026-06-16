# GW2Radar API Access Governance

All external GW2 API access must go through `Gw2ApiGateway`.

Required flow:

```text
Feature module
-> Gw2ApiGateway
-> Cache check
-> Rate limiter
-> Request queue
-> GW2 API client
-> Evidence writer
-> Normalizer / Graph builder
-> Inference
-> Report
```

Business, inference, report, graph, and API route modules must not call external GW2 API endpoints directly.

## API Key Safety

- Never log API keys.
- Never store API keys in raw evidence.
- Never include API keys in reports.
- Never include API keys in exception messages.
- Mask API keys in debugging output.
- Support deletion of API key and account snapshots before production account integrations.
- Use environment variables for local development.
- Use encrypted storage for production.

## Rate Limit Policy

MVP defaults:

```yaml
gw2_api_rate_limit:
  scope: outbound_ip
  burst_capacity: 250
  refill_rate_per_second: 4
  hard_max_per_minute: 240
```

The system must cache first, batch where supported, deduplicate requests, retry with backoff, and never bypass official limits.

Forbidden:

- proxy pools;
- IP rotation;
- 429-triggered IP switching;
- high-frequency scraping;
- rate-limit evasion.

## 429 Handling

When HTTP 429 occurs:

- record endpoint, params hash, request id, and timestamp;
- do not log API keys;
- do not switch IP;
- apply exponential backoff;
- reduce global request rate for future requests;
- return `rate_limited_retrying` or `refresh_pending` to callers until retries are exhausted.

## Endpoint TTL Defaults

```yaml
items: 72h
recipes: 72h
achievements: 72h
currencies: 72h
account: 30m
characters: 30m
wallet: 30m
materials: 30m
bank: 30m
account_achievements: 60m
commerce_prices_goal_items: 30m
commerce_listings: 60m
```

## Batch Requirement

Where supported, use batch endpoints such as:

- items;
- recipes;
- achievements;
- commerce prices;
- commerce listings;
- skins;
- traits;
- skills.

Avoid N+1 request patterns.
