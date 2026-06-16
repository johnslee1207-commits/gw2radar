# MVP 0.3.4 Growth Website + CMS + Payment Abstraction

Date: 2026-06-16

## Scope

This milestone implements P12 Growth Website + CMS + Payment Abstraction after the P6-P9 individual-player commercial product loop.

## Implemented

- CMS page model.
- Landing page seed content.
- SEO metadata support.
- Pricing plan model.
- Payment provider protocol.
- Mock payment provider.
- Checkout session model.
- Subscription model.
- Webhook event model.
- Entitlement integration after checkout completion.
- Mandatory trust pages:
  - Privacy;
  - Terms;
  - API Key Safety.
- Versioned Growth API routes:

```http
GET  /api/v1/growth/pages
GET  /api/v1/growth/pages/{slug}
GET  /api/v1/growth/pricing
POST /api/v1/growth/checkout
POST /api/v1/growth/checkout/{checkout_session_id}/complete
```

## Commercial Boundaries

- No real payment provider integration yet.
- Mock checkout is deterministic and test-only.
- The domain model does not lock to a provider.
- GW2Radar does not sell official API access.
- GW2Radar does not sell player data.
- API key safety and privacy pages are mandatory.

## Verification

Added tests:

- `tests/test_landing_pages.py`;
- `tests/test_cms_content.py`;
- `tests/test_pricing_model.py`;
- `tests/test_payment_provider_mock.py`;
- `tests/test_entitlement_after_payment.py`;
- `tests/test_privacy_page_required.py`;
- `tests/test_growth_api.py`.

Required verification:

```text
python -m pytest
python harness/run_smoke.py
python harness/run_sync_smoke.py
python -m alembic upgrade head
```

## Next Milestone

P10 Guild / Static Readiness Console:

- guild model;
- team model;
- team member consent;
- role coverage inference;
- team readiness score;
- privacy-safe member summary;
- guild readiness report.
