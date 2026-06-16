from fastapi import APIRouter, HTTPException, Response

from gw2radar.api.envelope import ApiDataEnvelope
from gw2radar.commercial.creator_intelligence import (
    CommunitySignalInput,
    build_creator_report,
    calculate_topic_trends,
    find_content_opportunities,
    import_community_signal,
    render_creator_report,
)
from gw2radar.db import session as db_session
from gw2radar.db.init_db import init_db

router = APIRouter(prefix="/api/v1/creator", tags=["creator"])


@router.post("/signals/import", response_model=ApiDataEnvelope)
def post_creator_signal_import(request: CommunitySignalInput) -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        try:
            signal = import_community_signal(session, request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiDataEnvelope(data={"signal": signal.model_dump(mode="json")})


@router.get("/topics", response_model=ApiDataEnvelope)
def get_creator_topics() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        trends = [trend.model_dump(mode="json") for trend in calculate_topic_trends(session)]
    return ApiDataEnvelope(data={"topics": trends})


@router.get("/opportunities", response_model=ApiDataEnvelope)
def get_creator_opportunities() -> ApiDataEnvelope:
    init_db()
    with db_session.SessionLocal() as session:
        opportunities = [item.model_dump(mode="json") for item in find_content_opportunities(session)]
    return ApiDataEnvelope(data={"opportunities": opportunities})


@router.post("/report")
def post_creator_report() -> Response:
    init_db()
    with db_session.SessionLocal() as session:
        report = build_creator_report(session)
        markdown = render_creator_report(report)
    return Response(content=markdown, media_type="text/markdown; charset=utf-8")
