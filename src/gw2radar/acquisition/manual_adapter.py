from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator
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
from gw2radar.acquisition.repository import create_job, create_raw_evidence, mark_job_succeeded, register_source, upsert_policy
from gw2radar.kb.kb_models import validate_kb_text


class ManualNoteImportInput(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    summary: str = Field(min_length=1, max_length=1200)
    kb_target: KbTarget = KbTarget.NONE
    reviewer: str = "manual_reviewer"
    source_note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_note(self) -> "ManualNoteImportInput":
        validate_kb_text(self.title, self.summary, self.source_note or "")
        return self


class WebSummaryImportInput(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    source_url: HttpUrl
    summary: str = Field(min_length=1, max_length=1200)
    source_type: Literal["gw2_wiki", "public_build_site", "community_signal"] = "gw2_wiki"
    kb_target: KbTarget = KbTarget.OFFICIAL
    attribution: str = Field(min_length=1, max_length=300)
    reviewer: str = "manual_reviewer"

    @model_validator(mode="after")
    def validate_summary(self) -> "WebSummaryImportInput":
        validate_kb_text(self.title, self.summary, self.attribution)
        return self


@dataclass(frozen=True)
class ManualAdapterResult:
    source_id: str
    job_id: str
    evidence_id: str
    source_type: str


def ingest_manual_note(session: Session, request: ManualNoteImportInput) -> ManualAdapterResult:
    source = register_source(
        session,
        AcquisitionSourceInput(
            name=request.title,
            source_type=AcquisitionSourceType.MANUAL_NOTE,
            acquisition_mode=AcquisitionMode.MANUAL,
            allowed_use=AllowedUse.MANUAL_NOTE,
            graph_target=GraphTarget.PERSONAL_INTELLIGENCE,
            kb_target=request.kb_target,
            trust_level=0.6,
            review_required=True,
            notes=request.source_note,
        ),
    )
    upsert_policy(
        session,
        source.source_id,
        SourcePolicyInput(
            allowed_use=AllowedUse.MANUAL_NOTE,
            refresh_mode=RefreshMode.MANUAL,
            can_drive_paid_report=False,
            can_drive_strong_recommendation=False,
            forbidden_use=["automated_trade", "public_private_data_mix"],
        ),
    )
    job = create_job(
        session,
        AcquisitionJobInput(
            source_id=source.source_id,
            job_type="manual_note_import",
            params={"title": request.title},
            requested_by=request.reviewer,
        ),
    )
    evidence = create_raw_evidence(
        session,
        RawEvidenceInput(
            source_id=source.source_id,
            job_id=job.job_id,
            content_type=ContentType.MANUAL_NOTE,
            title=request.title,
            summary=request.summary,
            metadata={"reviewer": request.reviewer, "kb_target": request.kb_target.value},
        ),
    )
    job = mark_job_succeeded(session, job.job_id)
    return ManualAdapterResult(
        source_id=source.source_id,
        job_id=job.job_id,
        evidence_id=evidence.evidence_id,
        source_type=source.source_type.value,
    )


def ingest_web_summary(session: Session, request: WebSummaryImportInput) -> ManualAdapterResult:
    source_type = AcquisitionSourceType(request.source_type)
    source = register_source(
        session,
        AcquisitionSourceInput(
            name=request.title,
            source_type=source_type,
            acquisition_mode=AcquisitionMode.WEB_SUMMARY,
            base_url=request.source_url,
            allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
            graph_target=GraphTarget.PUBLIC_GAME,
            kb_target=request.kb_target,
            trust_level=_trust_level_for_source(source_type),
            review_required=True,
            notes=request.attribution,
        ),
    )
    upsert_policy(
        session,
        source.source_id,
        SourcePolicyInput(
            allowed_use=AllowedUse.SUMMARY_AND_REFERENCE,
            refresh_mode=RefreshMode.MANUAL,
            can_drive_paid_report=source_type != AcquisitionSourceType.COMMUNITY_SIGNAL,
            can_drive_strong_recommendation=False,
            retain_raw_evidence=False,
            forbidden_use=["full_text_copy", "automated_trade", "public_private_data_mix"],
            attribution_required=True,
        ),
    )
    job = create_job(
        session,
        AcquisitionJobInput(
            source_id=source.source_id,
            job_type="web_summary_import",
            params={"source_url": str(request.source_url), "source_type": request.source_type},
            requested_by=request.reviewer,
        ),
    )
    evidence = create_raw_evidence(
        session,
        RawEvidenceInput(
            source_id=source.source_id,
            job_id=job.job_id,
            content_type=ContentType.MARKDOWN,
            title=request.title,
            source_url=str(request.source_url),
            summary=request.summary,
            metadata={
                "attribution": request.attribution,
                "reviewer": request.reviewer,
                "kb_target": request.kb_target.value,
                "summary_only": True,
            },
        ),
    )
    job = mark_job_succeeded(session, job.job_id)
    return ManualAdapterResult(
        source_id=source.source_id,
        job_id=job.job_id,
        evidence_id=evidence.evidence_id,
        source_type=source.source_type.value,
    )


def _trust_level_for_source(source_type: AcquisitionSourceType) -> float:
    if source_type == AcquisitionSourceType.GW2_WIKI:
        return 0.75
    if source_type == AcquisitionSourceType.PUBLIC_BUILD_SITE:
        return 0.65
    return 0.4
