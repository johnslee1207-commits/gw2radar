from pathlib import Path
import shutil
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
from gw2radar.acquisition.promotion_queue import (
    build_acquisition_promotion_queue,
    render_acquisition_promotion_queue_markdown,
)
from gw2radar.acquisition.repository import create_raw_evidence, register_source
from gw2radar.api.main import app
from gw2radar.db.init_db import init_db
from gw2radar.db.session import close_database, configure_database
from gw2radar.kb.kb_models import KnowledgeDomain, KnowledgeReviewStatus, KnowledgeRuleInput
from gw2radar.kb.kb_repository import create_rule


def test_promotion_queue_empty_registry_is_read_only() -> None:
    temp_dir = Path(".test_tmp") / f"promotion-empty-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'promotion.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            queue = build_acquisition_promotion_queue(session)
            markdown = render_acquisition_promotion_queue_markdown(queue)

        assert queue.schema_version == "gw2radar.acquisition_promotion_queue.v1"
        assert queue.item_count == 0
        assert "# Acquisition Evidence Promotion Queue" in markdown
        assert "does not persist, enable, or promote" in markdown
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_promotion_queue_flags_registered_source_without_raw_evidence() -> None:
    temp_dir = Path(".test_tmp") / f"promotion-source-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'promotion.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            source = register_source(
                session,
                AcquisitionSourceInput(
                    name="Official News PDFs",
                    source_type=AcquisitionSourceType.DOWNLOADED_PDF,
                    acquisition_mode=AcquisitionMode.LOCAL_FILE,
                    local_path="docs/knowledge_base/_sources/pdf/news",
                    allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                    graph_target=GraphTarget.PUBLIC_GAME,
                    kb_target=KbTarget.OFFICIAL,
                    review_required=True,
                ),
            )
            queue = build_acquisition_promotion_queue(session)

        assert queue.item_count == 1
        item = queue.items[0]
        assert item.item_type == "source_needs_raw_evidence"
        assert item.priority == "P1"
        assert item.source_id == source.source_id
        assert "Manual review is required" in item.safety_notes[0]
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_promotion_queue_flags_evidence_without_article_or_rule_candidate() -> None:
    temp_dir = Path(".test_tmp") / f"promotion-evidence-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'promotion.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            source = register_source(
                session,
                AcquisitionSourceInput(
                    name="Manual Patch Summary",
                    source_type=AcquisitionSourceType.MANUAL_NOTE,
                    acquisition_mode=AcquisitionMode.MANUAL,
                    allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                    graph_target=GraphTarget.PUBLIC_GAME,
                    kb_target=KbTarget.OFFICIAL,
                    review_required=True,
                ),
            )
            evidence = create_raw_evidence(
                session,
                RawEvidenceInput(
                    source_id=source.source_id,
                    content_type=ContentType.MANUAL_NOTE,
                    title="Patch summary evidence",
                    payload_hash="b" * 64,
                    summary="Reviewed summary-only notes for a patch impact review.",
                ),
            )
            queue = build_acquisition_promotion_queue(session)

        item_types = {item.item_type for item in queue.items}
        assert item_types == {"source_needs_kb_article", "raw_evidence_needs_rule_candidate"}
        assert all(evidence.evidence_id in item.evidence_refs for item in queue.items)
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_promotion_queue_flags_rule_refs_without_raw_evidence() -> None:
    temp_dir = Path(".test_tmp") / f"promotion-rule-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{temp_dir / 'promotion.db'}")
    session_factory = sessionmaker(bind=engine)
    try:
        init_db(engine)
        with session_factory() as session:
            rule = create_rule(
                session,
                KnowledgeRuleInput(
                    name="Document-only rule",
                    domain=KnowledgeDomain.OFFICIAL,
                    condition="source_summary_mentions:balance_update",
                    recommendation="Review affected builds before surfacing patch-impact advice.",
                    action_type="review_patch_impact",
                    priority_delta=0.1,
                    explanation_template="A reviewed document summary suggests a patch-impact review is needed.",
                    evidence_refs=["doc-only-ref"],
                    confidence=0.8,
                    review_status=KnowledgeReviewStatus.REVIEWED,
                    enabled=False,
                ),
            )
            queue = build_acquisition_promotion_queue(session)

        assert queue.item_count == 1
        assert queue.items[0].item_type == "rule_needs_raw_evidence"
        assert queue.items[0].rule_id == rule.rule_id
        assert queue.items[0].evidence_refs == ["doc-only-ref"]
    finally:
        engine.dispose()
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_promotion_queue_api_and_markdown_export() -> None:
    temp_dir = Path(".test_tmp") / f"promotion-api-{uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        configure_database(f"sqlite:///{temp_dir / 'api.db'}")
        init_db()
        client = TestClient(app)
        response = client.get("/api/v1/acquisition/promotion-queue")
        markdown = client.get("/api/v1/acquisition/promotion-queue/export")
        bad = client.get("/api/v1/acquisition/promotion-queue/export?format=json")

        assert response.status_code == 200
        assert response.json()["data"]["queue"]["schema_version"] == "gw2radar.acquisition_promotion_queue.v1"
        assert markdown.status_code == 200
        assert markdown.headers["content-type"].startswith("text/markdown")
        assert "Acquisition Evidence Promotion Queue" in markdown.text
        assert bad.status_code == 400
    finally:
        close_database()
        shutil.rmtree(temp_dir, ignore_errors=True)
