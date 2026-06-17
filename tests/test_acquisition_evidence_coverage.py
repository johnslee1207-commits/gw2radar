from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from gw2radar.acquisition.coverage import build_evidence_coverage_map, render_evidence_coverage_markdown
from gw2radar.acquisition.models import (
    AcquisitionMode,
    AcquisitionSourceInput,
    AcquisitionSourceType,
    AllowedUse,
    ContentType,
    GraphTarget,
    KbTarget,
    RawEvidenceInput,
)
from gw2radar.acquisition.repository import create_raw_evidence, register_source
from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.models import KnowledgeArticleModel, utc_now
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_models import KnowledgeDomain, KnowledgeReviewStatus, KnowledgeRuleInput
from gw2radar.kb.kb_repository import create_rule


def test_evidence_coverage_empty_registry_reports_gaps() -> None:
    temp_dir = Path(".test_tmp") / f"coverage-empty-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'coverage.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            report = build_evidence_coverage_map(session)
            markdown = render_evidence_coverage_markdown(report)

        assert report.schema_version == "gw2radar.acquisition_evidence_coverage.v1"
        assert report.source_count == 0
        assert report.raw_evidence_count == 0
        assert "# Acquisition Evidence Coverage Map" in markdown
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_evidence_coverage_links_source_raw_evidence_article_and_rule() -> None:
    temp_dir = Path(".test_tmp") / f"coverage-linked-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'coverage.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            source = register_source(
                session,
                AcquisitionSourceInput(
                    name="Official Items API",
                    source_type=AcquisitionSourceType.OFFICIAL_API_PUBLIC,
                    acquisition_mode=AcquisitionMode.API,
                    base_url="https://api.guildwars2.com",
                    allowed_use=AllowedUse.API_JSON,
                    graph_target=GraphTarget.PUBLIC_GAME,
                    kb_target=KbTarget.OFFICIAL,
                    review_required=False,
                ),
            )
            evidence = create_raw_evidence(
                session,
                RawEvidenceInput(
                    source_id=source.source_id,
                    content_type=ContentType.API_JSON,
                    title="Items API response",
                    payload_hash="a" * 64,
                    summary="Summary-only evidence for official items endpoint.",
                ),
            )
            session.add(
                KnowledgeArticleModel(
                    kb_id="kb_article_coverage",
                    title="Items API source note",
                    domain="official",
                    content_type="source_note",
                    summary="Source-linked summary.",
                    body_markdown="Reviewed summary only.",
                    source_refs_json=[source.source_id],
                    linked_entities_json=[],
                    linked_relations_json=[],
                    linked_actions_json=[],
                    confidence=0.8,
                    review_status="reviewed",
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
            )
            session.commit()
            create_rule(
                session,
                KnowledgeRuleInput(
                    name="Items evidence rule",
                    domain=KnowledgeDomain.OFFICIAL,
                    condition="source_has_raw_evidence:items",
                    recommendation="Use official item evidence when explaining public item data.",
                    action_type="refresh_public_static_data",
                    priority_delta=0.1,
                    explanation_template="Official item evidence is available for this recommendation.",
                    evidence_refs=[evidence.evidence_id],
                    confidence=0.8,
                    review_status=KnowledgeReviewStatus.REVIEWED,
                    enabled=False,
                ),
            )
            report = build_evidence_coverage_map(session)

        row = report.source_rows[0]
        assert row.coverage_status == "covered"
        assert row.raw_evidence_count == 1
        assert row.kb_article_count == 1
        assert row.knowledge_rule_count == 1
        assert report.covered_source_count == 1
        assert report.rule_ids_without_raw_evidence == []
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_evidence_coverage_api_and_markdown_export() -> None:
    temp_dir = Path(".test_tmp") / f"coverage-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        client = TestClient(app)
        response = client.get("/api/v1/acquisition/evidence-coverage")
        markdown = client.get("/api/v1/acquisition/evidence-coverage/export")
        bad = client.get("/api/v1/acquisition/evidence-coverage/export?format=json")

        assert response.status_code == 200
        assert response.json()["data"]["coverage"]["schema_version"] == "gw2radar.acquisition_evidence_coverage.v1"
        assert markdown.status_code == 200
        assert markdown.headers["content-type"].startswith("text/markdown")
        assert "Acquisition Evidence Coverage Map" in markdown.text
        assert bad.status_code == 400
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)
