from dataclasses import dataclass

from sqlalchemy.orm import Session

from gw2radar.acquisition.models import (
    AcquisitionJobInput,
    AcquisitionMode,
    AcquisitionSourceInput,
    AcquisitionSourceType,
    AllowedUse,
    ContentType,
    GraphTarget,
    KbTarget,
    RawEvidenceInput,
    RefreshMode,
    SourcePolicyInput,
)
from gw2radar.acquisition.repository import (
    create_job,
    create_raw_evidence,
    get_raw_evidence_by_hash,
    get_source_by_local_path,
    mark_job_succeeded,
    register_source,
    upsert_policy,
)
from gw2radar.kb_pdf.pdf_evidence_writer import build_evidence_records
from gw2radar.kb_pdf.pdf_inventory import PdfSourceRecord


@dataclass(frozen=True)
class LocalPdfAdapterResult:
    source_count: int
    new_source_count: int
    evidence_count: int
    new_evidence_count: int
    job_count: int


def ingest_pdf_inventory_as_acquisition_sources(
    session: Session,
    records: list[PdfSourceRecord],
    requested_by: str = "local_pdf_adapter",
) -> LocalPdfAdapterResult:
    new_sources = 0
    new_evidence = 0
    job_count = 0
    evidence_by_pdf_id = {record.evidence_id.replace("evidence:pdf:", "pdf:", 1): record for record in build_evidence_records(records)}

    for record in records:
        source = get_source_by_local_path(session, record.path)
        if source is None:
            source = register_source(
                session,
                AcquisitionSourceInput(
                    name=record.file_name,
                    source_type=_source_type_for_category(record.category),
                    acquisition_mode=AcquisitionMode.LOCAL_FILE,
                    local_path=record.path,
                    allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                    graph_target=GraphTarget.PUBLIC_GAME,
                    kb_target=_kb_target_for_category(record.category),
                    trust_level=evidence_by_pdf_id[record.pdf_id].confidence,
                    review_required=True,
                    notes=f"Local downloaded PDF inventory record: {record.pdf_id}",
                ),
            )
            new_sources += 1

        upsert_policy(
            session,
            source.source_id,
            SourcePolicyInput(
                allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
                refresh_mode=RefreshMode.MANUAL,
                can_drive_paid_report=_can_drive_paid_report(record.category),
                can_drive_strong_recommendation=False,
                retain_raw_evidence=False,
                forbidden_use=["full_text_copy", "automated_trade", "public_private_data_mix"],
            ),
        )

        job = create_job(
            session,
            AcquisitionJobInput(
                source_id=source.source_id,
                job_type="local_pdf_inventory_import",
                params={"pdf_id": record.pdf_id, "sha256": record.sha256, "category": record.category},
                requested_by=requested_by,
            ),
        )
        mark_job_succeeded(session, job.job_id)
        job_count += 1

        if get_raw_evidence_by_hash(session, source.source_id, record.sha256) is None:
            create_raw_evidence(
                session,
                RawEvidenceInput(
                    source_id=source.source_id,
                    job_id=job.job_id,
                    content_type=ContentType.PDF,
                    title=record.file_name,
                    payload_ref=record.path,
                    payload_hash=record.sha256,
                    summary=f"Downloaded PDF source classified as {record.category}; see payload_ref for local file.",
                    metadata={
                        "pdf_id": record.pdf_id,
                        "file_size": record.size_bytes,
                        "category": record.category,
                        "year": record.year,
                        "priority": record.priority,
                        "status": record.status,
                    },
                ),
            )
            new_evidence += 1

    return LocalPdfAdapterResult(
        source_count=len(records),
        new_source_count=new_sources,
        evidence_count=len(records),
        new_evidence_count=new_evidence,
        job_count=job_count,
    )


def _source_type_for_category(category: str) -> AcquisitionSourceType:
    if category == "patch_note":
        return AcquisitionSourceType.OFFICIAL_PATCH_NOTE
    return AcquisitionSourceType.DOWNLOADED_PDF


def _kb_target_for_category(category: str) -> KbTarget:
    if category in {"build_site", "build"}:
        return KbTarget.BUILD
    if category in {"market", "trading_post"}:
        return KbTarget.MARKET
    return KbTarget.OFFICIAL


def _can_drive_paid_report(category: str) -> bool:
    return category in {
        "official_api",
        "official_api_endpoint",
        "api_governance",
        "api_permission",
        "api_key",
        "official_news",
        "arenanet_policy",
        "patch_note",
    }
