from datetime import datetime
from enum import StrEnum
from typing import Protocol
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from gw2radar.commercial.report_engine import create_report_entitlement, ensure_default_report_products
from gw2radar.db.models import (
    CheckoutSessionModel,
    CmsPageModel,
    PricingPlanModel,
    SubscriptionModel,
    WebhookEventModel,
    utc_now,
)


DEFAULT_USER_ID = "local-user"


class CmsPageType(StrEnum):
    LANDING = "landing"
    BLOG = "blog"
    FAQ = "faq"
    PRICING = "pricing"
    DOCS = "docs"
    PRIVACY = "privacy"
    TERMS = "terms"
    API_KEY_SAFETY = "api_key_safety"


class BillingInterval(StrEnum):
    ONE_TIME = "one_time"
    MONTHLY = "monthly"


class CheckoutStatus(StrEnum):
    CREATED = "created"
    PAID = "paid"
    CANCELED = "canceled"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    CANCELED = "canceled"


class SeoMetadata(BaseModel):
    title: str
    description: str
    canonical_path: str


class CmsPage(BaseModel):
    page_id: str
    slug: str
    title: str
    page_type: CmsPageType
    body_markdown: str
    seo: SeoMetadata
    published: bool = True
    created_at: datetime
    updated_at: datetime


class PricingPlan(BaseModel):
    plan_id: str
    name: str
    product_id: str
    price_cents: int
    billing_interval: BillingInterval
    enabled: bool = True
    features: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CheckoutSession(BaseModel):
    checkout_session_id: str
    user_id: str
    plan_id: str
    product_id: str
    provider: str
    status: CheckoutStatus
    checkout_url: str
    created_at: datetime
    completed_at: datetime | None = None


class Subscription(BaseModel):
    subscription_id: str
    user_id: str
    plan_id: str
    product_id: str
    status: SubscriptionStatus
    created_at: datetime
    current_period_end: datetime | None = None


class WebhookEvent(BaseModel):
    webhook_event_id: str
    provider: str
    event_type: str
    payload: dict
    processed: bool
    created_at: datetime


class CheckoutRequest(BaseModel):
    plan_id: str
    user_id: str = DEFAULT_USER_ID


class PaymentProvider(Protocol):
    provider_name: str

    def create_checkout_session(self, session: Session, request: CheckoutRequest) -> CheckoutSession:
        ...

    def complete_checkout_session(self, session: Session, checkout_session_id: str) -> CheckoutSession:
        ...


DEFAULT_PAGES = [
    (
        "home",
        "GW2Radar",
        CmsPageType.LANDING,
        "Evidence-backed Guild Wars 2 planning reports. GW2Radar sells planning intelligence, not official API access.",
        "GW2Radar planning reports",
        "Personal legendary, build, and market planning reports for Guild Wars 2.",
    ),
    (
        "returner-report",
        "Returner Report",
        CmsPageType.LANDING,
        "A free preview and paid report for players returning to Guild Wars 2.",
        "Returner report",
        "Understand what your account can do next without exposing raw private data.",
    ),
    (
        "legendary-planner",
        "Legendary Planner Pro",
        CmsPageType.LANDING,
        "Multi-goal legendary planning with do-not-sell recommendations and evidence labels.",
        "Legendary planner",
        "Plan legendary goals with account-aware material reservations.",
    ),
    (
        "build-fit",
        "Build Fit Advisor",
        CmsPageType.LANDING,
        "Check whether your account can play a structured build and what gear transition is required.",
        "Build fit advisor",
        "Account-aware build fit and gear transition planning.",
    ),
    (
        "market-radar",
        "Market Radar Pro",
        CmsPageType.LANDING,
        "Observe price trends and goal-aware material signals without automated trading.",
        "Market radar",
        "Market observation for planning, not trading automation.",
    ),
    (
        "pricing",
        "Pricing",
        CmsPageType.PRICING,
        "One-time reports and personal subscriptions are unlocked through entitlements.",
        "GW2Radar pricing",
        "Pricing for GW2Radar planning reports.",
    ),
    (
        "privacy",
        "Privacy",
        CmsPageType.PRIVACY,
        "Private player data can be deleted. GW2Radar does not sell player data.",
        "GW2Radar privacy",
        "How GW2Radar handles private player data.",
    ),
    (
        "terms",
        "Terms",
        CmsPageType.TERMS,
        "GW2Radar provides informational planning only and does not automate gameplay or trading.",
        "GW2Radar terms",
        "Terms for GW2Radar planning reports.",
    ),
    (
        "api-key-safety",
        "API Key Safety",
        CmsPageType.API_KEY_SAFETY,
        "Use read-only GW2 API permissions where possible. API keys are never returned by report routes.",
        "GW2Radar API key safety",
        "How GW2Radar protects GW2 API keys.",
    ),
]

DEFAULT_PLANS = [
    ("plan_returner_once", "Returner Full Recovery Report", "returner_full_report", 1000, BillingInterval.ONE_TIME),
    ("plan_legendary_once", "Legendary Planner Pro Report", "legendary_planner_pro_report", 1500, BillingInterval.ONE_TIME),
    ("plan_build_fit_once", "Build Fit Report", "build_fit_report", 1200, BillingInterval.ONE_TIME),
    ("plan_market_once", "Market Snapshot Report", "market_snapshot_report", 700, BillingInterval.ONE_TIME),
    ("plan_personal_monthly", "Personal Intelligence Monthly", "legendary_planner_pro_report", 900, BillingInterval.MONTHLY),
]


class MockPaymentProvider:
    provider_name = "mock_payment"

    def create_checkout_session(self, session: Session, request: CheckoutRequest) -> CheckoutSession:
        plan = session.get(PricingPlanModel, request.plan_id)
        if plan is None or not plan.enabled:
            raise ValueError("Unknown or disabled pricing plan.")
        row = CheckoutSessionModel(
            checkout_session_id=f"checkout_{uuid4().hex}",
            user_id=request.user_id,
            plan_id=plan.plan_id,
            product_id=plan.product_id,
            provider=self.provider_name,
            status=CheckoutStatus.CREATED.value,
            checkout_url=f"https://checkout.invalid/{plan.plan_id}",
            created_at=utc_now(),
        )
        session.add(row)
        session.commit()
        return _checkout_from_model(row)

    def complete_checkout_session(self, session: Session, checkout_session_id: str) -> CheckoutSession:
        checkout = session.get(CheckoutSessionModel, checkout_session_id)
        if checkout is None:
            raise ValueError("Checkout session not found.")
        checkout.status = CheckoutStatus.PAID.value
        checkout.completed_at = utc_now()
        session.add(
            WebhookEventModel(
                webhook_event_id=f"webhook_{uuid4().hex}",
                provider=self.provider_name,
                event_type="checkout.session.completed",
                payload_json={"checkout_session_id": checkout_session_id, "product_id": checkout.product_id},
                processed=True,
                created_at=utc_now(),
            )
        )
        plan = session.get(PricingPlanModel, checkout.plan_id)
        if plan and plan.billing_interval == BillingInterval.MONTHLY.value:
            session.add(
                SubscriptionModel(
                    subscription_id=f"sub_{uuid4().hex}",
                    user_id=checkout.user_id,
                    plan_id=checkout.plan_id,
                    product_id=checkout.product_id,
                    status=SubscriptionStatus.ACTIVE.value,
                    created_at=utc_now(),
                )
            )
        create_report_entitlement(session, checkout.user_id, checkout.product_id)
        session.commit()
        return _checkout_from_model(checkout)


def ensure_growth_defaults(session: Session) -> None:
    ensure_default_report_products(session)
    for slug, title, page_type, body, seo_title, seo_description in DEFAULT_PAGES:
        if _page_by_slug(session, slug) is None:
            session.add(
                CmsPageModel(
                    page_id=f"page_{slug}",
                    slug=slug,
                    title=title,
                    page_type=page_type.value,
                    body_markdown=body,
                    seo_json={
                        "title": seo_title,
                        "description": seo_description,
                        "canonical_path": f"/{slug}" if slug != "home" else "/",
                    },
                    published=True,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
    for plan_id, name, product_id, price_cents, interval in DEFAULT_PLANS:
        if session.get(PricingPlanModel, plan_id) is None:
            session.add(
                PricingPlanModel(
                    plan_id=plan_id,
                    name=name,
                    product_id=product_id,
                    price_cents=price_cents,
                    billing_interval=interval.value,
                    enabled=True,
                    features_json=["evidence-backed report", "artifact export", "manual recommendations only"],
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
    session.commit()
    validate_required_trust_pages(session)


def list_pages(session: Session) -> list[CmsPage]:
    ensure_growth_defaults(session)
    return [_page_from_model(row) for row in session.query(CmsPageModel).order_by(CmsPageModel.slug).all()]


def get_page(session: Session, slug: str) -> CmsPage | None:
    ensure_growth_defaults(session)
    row = _page_by_slug(session, slug)
    return _page_from_model(row) if row else None


def list_pricing_plans(session: Session) -> list[PricingPlan]:
    ensure_growth_defaults(session)
    rows = session.query(PricingPlanModel).filter(PricingPlanModel.enabled.is_(True)).order_by(PricingPlanModel.plan_id).all()
    return [_plan_from_model(row) for row in rows]


def create_checkout(session: Session, request: CheckoutRequest, provider: PaymentProvider | None = None) -> CheckoutSession:
    ensure_growth_defaults(session)
    return (provider or MockPaymentProvider()).create_checkout_session(session, request)


def complete_checkout(session: Session, checkout_session_id: str, provider: PaymentProvider | None = None) -> CheckoutSession:
    return (provider or MockPaymentProvider()).complete_checkout_session(session, checkout_session_id)


def validate_required_trust_pages(session: Session) -> None:
    required = {"privacy", "api-key-safety", "terms"}
    present = {row.slug for row in session.query(CmsPageModel).filter(CmsPageModel.slug.in_(required)).all()}
    missing = required - present
    if missing:
        raise ValueError(f"Missing required trust pages: {', '.join(sorted(missing))}")


def _page_by_slug(session: Session, slug: str) -> CmsPageModel | None:
    return session.query(CmsPageModel).filter(CmsPageModel.slug == slug).first()


def _page_from_model(row: CmsPageModel) -> CmsPage:
    return CmsPage(
        page_id=row.page_id,
        slug=row.slug,
        title=row.title,
        page_type=CmsPageType(row.page_type),
        body_markdown=row.body_markdown,
        seo=SeoMetadata(**row.seo_json),
        published=row.published,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _plan_from_model(row: PricingPlanModel) -> PricingPlan:
    return PricingPlan(
        plan_id=row.plan_id,
        name=row.name,
        product_id=row.product_id,
        price_cents=row.price_cents,
        billing_interval=BillingInterval(row.billing_interval),
        enabled=row.enabled,
        features=row.features_json,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _checkout_from_model(row: CheckoutSessionModel) -> CheckoutSession:
    return CheckoutSession(
        checkout_session_id=row.checkout_session_id,
        user_id=row.user_id,
        plan_id=row.plan_id,
        product_id=row.product_id,
        provider=row.provider,
        status=CheckoutStatus(row.status),
        checkout_url=row.checkout_url,
        created_at=row.created_at,
        completed_at=row.completed_at,
    )
