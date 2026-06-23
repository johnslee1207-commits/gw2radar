from fastapi import APIRouter, HTTPException

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.commercial.growth import (
    CheckoutRequest,
    complete_checkout,
    create_checkout,
    get_page,
    list_pages,
    list_pricing_plans,
)
from gw2radar.commercial.growth_retention import (
    MockEmailRequest,
    WeeklyReportRequest,
    build_report_history,
    build_retention_status,
    build_safe_share_preview,
    build_weekly_report_job,
    queue_mock_email_delivery,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db

router = APIRouter(prefix="/api/v1/growth", tags=["growth"])


@router.get("/pages", response_model=ApiDataEnvelope)
def get_growth_pages() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        pages = [page.model_dump(mode="json") for page in list_pages(session)]
    return ApiDataEnvelope(data={"pages": pages})


@router.get("/pages/{slug}", response_model=ApiDataEnvelope)
def get_growth_page(slug: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        page = get_page(session, slug)
    if page is None:
        raise HTTPException(status_code=404, detail="Page not found")
    return ApiDataEnvelope(data={"page": page.model_dump(mode="json")})


@router.get("/pricing", response_model=ApiDataEnvelope)
def get_growth_pricing() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        plans = [plan.model_dump(mode="json") for plan in list_pricing_plans(session)]
    return ApiDataEnvelope(data={"plans": plans})


@router.post("/checkout", response_model=ApiDataEnvelope)
def post_growth_checkout(request: CheckoutRequest) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            checkout = create_checkout(session, request)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"checkout": checkout.model_dump(mode="json")})


@router.post("/checkout/{checkout_session_id}/complete", response_model=ApiDataEnvelope)
def post_growth_checkout_complete(checkout_session_id: str) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            checkout = complete_checkout(session, checkout_session_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"checkout": checkout.model_dump(mode="json")})


@router.get("/retention/report-history", response_model=ApiDataEnvelope)
def get_growth_report_history(user_id: str = "local-user", limit: int = 10) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        history = [entry.model_dump(mode="json") for entry in build_report_history(session, user_id, limit=limit)]
    return ApiDataEnvelope(data={"history": history})


@router.post("/retention/weekly-report", response_model=ApiDataEnvelope)
def post_growth_weekly_report(request: WeeklyReportRequest) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        job = build_weekly_report_job(session, request)
    return ApiDataEnvelope(data={"weekly_report": job.model_dump(mode="json")})


@router.get("/retention/share-preview", response_model=ApiDataEnvelope)
def get_growth_share_preview(user_id: str = "local-user") -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        preview = build_safe_share_preview(session, user_id)
    return ApiDataEnvelope(data={"share_preview": preview.model_dump(mode="json")})


@router.post("/retention/mock-email", response_model=ApiDataEnvelope)
def post_growth_mock_email(request: MockEmailRequest) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        delivery = queue_mock_email_delivery(session, request)
    return ApiDataEnvelope(data={"delivery": delivery.model_dump(mode="json")})


@router.get("/retention/status", response_model=ApiDataEnvelope)
def get_growth_retention_status(user_id: str = "local-user") -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        status = build_retention_status(session, user_id)
    return ApiDataEnvelope(data={"retention": status.model_dump(mode="json")})
