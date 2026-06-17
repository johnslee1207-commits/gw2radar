from uuid import uuid4

from sqlalchemy.orm import Session

from gw2radar.acquisition.freshness import build_source_health
from gw2radar.acquisition.models import (
    AcquisitionJob,
    AcquisitionJobInput,
    AcquisitionJobStatus,
    AcquisitionSource,
    AcquisitionSourceInput,
    RawEvidence,
    RawEvidenceInput,
    ReviewStatus,
    SourceHealth,
    SourcePolicy,
    SourcePolicyInput,
)
from gw2radar.db.models import (
    AcquisitionJobModel,
    AcquisitionSourceModel,
    RawEvidenceModel,
    SourcePolicyModel,
    utc_now,
)


def register_source(session: Session, source: AcquisitionSourceInput) -> AcquisitionSource:
    now = utc_now()
    row = AcquisitionSourceModel(
        source_id=f"acq_source_{uuid4().hex}",
        name=source.name.strip(),
        source_type=source.source_type.value,
        acquisition_mode=source.acquisition_mode.value,
        base_url=str(source.base_url) if source.base_url else None,
        local_path=source.local_path,
        allowed_use=source.allowed_use.value,
        graph_target=source.graph_target.value,
        kb_target=source.kb_target.value,
        trust_level=source.trust_level,
        review_required=source.review_required,
        review_status=ReviewStatus.DRAFT.value,
        enabled=source.enabled,
        notes=source.notes,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.commit()
    return _source_from_model(row)


def list_sources(session: Session, source_type: str | None = None, kb_target: str | None = None) -> list[AcquisitionSource]:
    query = session.query(AcquisitionSourceModel)
    if source_type:
        query = query.filter(AcquisitionSourceModel.source_type == source_type)
    if kb_target:
        query = query.filter(AcquisitionSourceModel.kb_target == kb_target)
    rows = query.order_by(AcquisitionSourceModel.name).all()
    return [_source_from_model(row) for row in rows]


def get_source(session: Session, source_id: str) -> AcquisitionSource | None:
    row = session.get(AcquisitionSourceModel, source_id)
    return _source_from_model(row) if row else None


def get_source_by_local_path(session: Session, local_path: str) -> AcquisitionSource | None:
    row = (
        session.query(AcquisitionSourceModel)
        .filter(AcquisitionSourceModel.local_path == local_path)
        .order_by(AcquisitionSourceModel.created_at.desc())
        .first()
    )
    return _source_from_model(row) if row else None


def mark_source_reviewed(session: Session, source_id: str) -> AcquisitionSource:
    row = session.get(AcquisitionSourceModel, source_id)
    if row is None:
        raise ValueError("Acquisition source not found.")
    row.review_status = ReviewStatus.REVIEWED.value
    row.updated_at = utc_now()
    session.commit()
    return _source_from_model(row)


def mark_source_deprecated(session: Session, source_id: str) -> AcquisitionSource:
    row = session.get(AcquisitionSourceModel, source_id)
    if row is None:
        raise ValueError("Acquisition source not found.")
    row.review_status = ReviewStatus.DEPRECATED.value
    row.enabled = False
    row.updated_at = utc_now()
    session.commit()
    return _source_from_model(row)


def upsert_policy(session: Session, source_id: str, policy: SourcePolicyInput) -> SourcePolicy:
    if session.get(AcquisitionSourceModel, source_id) is None:
        raise ValueError("Acquisition source not found.")
    row = (
        session.query(SourcePolicyModel)
        .filter(SourcePolicyModel.source_id == source_id)
        .order_by(SourcePolicyModel.created_at.desc())
        .first()
    )
    now = utc_now()
    if row is None:
        row = SourcePolicyModel(
            policy_id=f"source_policy_{uuid4().hex}",
            source_id=source_id,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
    row.allowed_use = policy.allowed_use.value
    row.refresh_mode = policy.refresh_mode.value
    row.refresh_interval_seconds = policy.refresh_interval_seconds
    row.freshness_required_for_strong_action = policy.freshness_required_for_strong_action
    row.can_drive_paid_report = policy.can_drive_paid_report
    row.can_drive_strong_recommendation = policy.can_drive_strong_recommendation
    row.retain_raw_evidence = policy.retain_raw_evidence
    row.forbidden_use_json = policy.forbidden_use
    row.attribution_required = policy.attribution_required
    row.updated_at = now
    session.commit()
    return _policy_from_model(row)


def get_policy(session: Session, source_id: str) -> SourcePolicy | None:
    row = (
        session.query(SourcePolicyModel)
        .filter(SourcePolicyModel.source_id == source_id)
        .order_by(SourcePolicyModel.created_at.desc())
        .first()
    )
    return _policy_from_model(row) if row else None


def create_job(session: Session, job: AcquisitionJobInput) -> AcquisitionJob:
    if session.get(AcquisitionSourceModel, job.source_id) is None:
        raise ValueError("Acquisition source not found.")
    now = utc_now()
    row = AcquisitionJobModel(
        job_id=f"acq_job_{uuid4().hex}",
        source_id=job.source_id,
        job_type=job.job_type.strip(),
        priority=job.priority.value,
        params_json=job.params,
        requested_by=job.requested_by.strip(),
        status=AcquisitionJobStatus.QUEUED.value,
        attempts=0,
        max_attempts=3,
        created_at=now,
        updated_at=now,
    )
    session.add(row)
    session.commit()
    return _job_from_model(row)


def list_jobs(
    session: Session,
    source_id: str | None = None,
    status: AcquisitionJobStatus | None = None,
) -> list[AcquisitionJob]:
    query = session.query(AcquisitionJobModel)
    if source_id:
        query = query.filter(AcquisitionJobModel.source_id == source_id)
    if status:
        query = query.filter(AcquisitionJobModel.status == status.value)
    rows = query.order_by(AcquisitionJobModel.created_at.desc()).all()
    return [_job_from_model(row) for row in rows]


def get_job(session: Session, job_id: str) -> AcquisitionJob | None:
    row = session.get(AcquisitionJobModel, job_id)
    return _job_from_model(row) if row else None


def mark_job_succeeded(session: Session, job_id: str) -> AcquisitionJob:
    row = session.get(AcquisitionJobModel, job_id)
    if row is None:
        raise ValueError("Acquisition job not found.")
    row.status = AcquisitionJobStatus.SUCCEEDED.value
    row.updated_at = utc_now()
    row.completed_at = row.updated_at
    session.commit()
    return _job_from_model(row)


def mark_job_skipped(session: Session, job_id: str, error_code: str, error: str) -> AcquisitionJob:
    row = session.get(AcquisitionJobModel, job_id)
    if row is None:
        raise ValueError("Acquisition job not found.")
    row.status = AcquisitionJobStatus.SKIPPED.value
    row.last_error_code = error_code
    row.last_error = error
    row.updated_at = utc_now()
    row.completed_at = row.updated_at
    session.commit()
    return _job_from_model(row)


def latest_job_for_source(session: Session, source_id: str) -> AcquisitionJob | None:
    row = (
        session.query(AcquisitionJobModel)
        .filter(AcquisitionJobModel.source_id == source_id)
        .order_by(AcquisitionJobModel.updated_at.desc())
        .first()
    )
    return _job_from_model(row) if row else None


def get_source_health(session: Session, source_id: str) -> SourceHealth:
    source = get_source(session, source_id)
    if source is None:
        raise ValueError("Acquisition source not found.")
    return build_source_health(source, get_policy(session, source_id), latest_job_for_source(session, source_id))


def create_raw_evidence(session: Session, evidence: RawEvidenceInput) -> RawEvidence:
    if session.get(AcquisitionSourceModel, evidence.source_id) is None:
        raise ValueError("Acquisition source not found.")
    now = utc_now()
    row = RawEvidenceModel(
        evidence_id=f"raw_evidence_{uuid4().hex}",
        source_id=evidence.source_id,
        job_id=evidence.job_id,
        content_type=evidence.content_type.value,
        title=evidence.title.strip(),
        source_url=evidence.source_url,
        payload_ref=evidence.payload_ref,
        payload_hash=evidence.payload_hash,
        summary=evidence.summary.strip(),
        metadata_json=evidence.metadata,
        created_at=now,
    )
    session.add(row)
    session.commit()
    return _evidence_from_model(row)


def get_raw_evidence_by_hash(session: Session, source_id: str, payload_hash: str) -> RawEvidence | None:
    row = (
        session.query(RawEvidenceModel)
        .filter(RawEvidenceModel.source_id == source_id, RawEvidenceModel.payload_hash == payload_hash)
        .order_by(RawEvidenceModel.created_at.desc())
        .first()
    )
    return _evidence_from_model(row) if row else None


def _source_from_model(row: AcquisitionSourceModel) -> AcquisitionSource:
    return AcquisitionSource(
        source_id=row.source_id,
        name=row.name,
        source_type=row.source_type,
        acquisition_mode=row.acquisition_mode,
        base_url=row.base_url,
        local_path=row.local_path,
        allowed_use=row.allowed_use,
        graph_target=row.graph_target,
        kb_target=row.kb_target,
        trust_level=row.trust_level,
        review_required=row.review_required,
        review_status=row.review_status,
        enabled=row.enabled,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _policy_from_model(row: SourcePolicyModel) -> SourcePolicy:
    return SourcePolicy(
        policy_id=row.policy_id,
        source_id=row.source_id,
        allowed_use=row.allowed_use,
        refresh_mode=row.refresh_mode,
        refresh_interval_seconds=row.refresh_interval_seconds,
        freshness_required_for_strong_action=row.freshness_required_for_strong_action,
        can_drive_paid_report=row.can_drive_paid_report,
        can_drive_strong_recommendation=row.can_drive_strong_recommendation,
        retain_raw_evidence=row.retain_raw_evidence,
        forbidden_use=row.forbidden_use_json,
        attribution_required=row.attribution_required,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _job_from_model(row: AcquisitionJobModel) -> AcquisitionJob:
    return AcquisitionJob(
        job_id=row.job_id,
        source_id=row.source_id,
        job_type=row.job_type,
        priority=row.priority,
        params=row.params_json,
        requested_by=row.requested_by,
        status=row.status,
        attempts=row.attempts,
        max_attempts=row.max_attempts,
        last_error_code=row.last_error_code,
        last_error=row.last_error,
        created_at=row.created_at,
        updated_at=row.updated_at,
        completed_at=row.completed_at,
    )


def _evidence_from_model(row: RawEvidenceModel) -> RawEvidence:
    return RawEvidence(
        evidence_id=row.evidence_id,
        source_id=row.source_id,
        job_id=row.job_id,
        content_type=row.content_type,
        title=row.title,
        source_url=row.source_url,
        payload_ref=row.payload_ref,
        payload_hash=row.payload_hash,
        summary=row.summary,
        metadata=row.metadata_json,
        created_at=row.created_at,
    )
