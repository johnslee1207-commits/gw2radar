from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class EntityModel(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    canonical_name: Mapped[str] = mapped_column(String, nullable=False)
    graph_layer: Mapped[str] = mapped_column(String, default="public_game")
    external_id: Mapped[str | None] = mapped_column(String, nullable=True)
    properties_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RelationModel(Base):
    __tablename__ = "relations"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    subject_id: Mapped[str] = mapped_column(String, nullable=False)
    predicate: Mapped[str] = mapped_column(String, nullable=False)
    object_id: Mapped[str] = mapped_column(String, nullable=False)
    graph_layer: Mapped[str] = mapped_column(String, default="public_game")
    properties_json: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence_id: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EvidenceModel(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    graph_layer: Mapped[str] = mapped_column(String, default="public_game")
    source_type: Mapped[str] = mapped_column(String, default="mock")
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    raw_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    payload_ref: Mapped[str | None] = mapped_column(String, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    license_note: Mapped[str | None] = mapped_column(String, nullable=True)


class PlayerStateModel(Base):
    __tablename__ = "player_state"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    account_id: Mapped[str] = mapped_column(String, nullable=False)
    entity_id: Mapped[str] = mapped_column(String, nullable=False)
    graph_layer: Mapped[str] = mapped_column(String, default="private_player_state")
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    location: Mapped[str | None] = mapped_column(String, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class ActionModel(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    graph_layer: Mapped[str] = mapped_column(String, default="personal_intelligence")
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    target_entity_id: Mapped[str | None] = mapped_column(String, nullable=True)
    target_goal_id: Mapped[str | None] = mapped_column(String, nullable=True)
    priority_score: Mapped[float] = mapped_column(Float, default=0.5)
    urgency: Mapped[str] = mapped_column(String, nullable=False)
    properties_json: Mapped[dict] = mapped_column(JSON, default=dict)
    explanation: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class RefreshQueueModel(Base):
    __tablename__ = "refresh_queue"

    request_id: Mapped[str] = mapped_column(String, primary_key=True)
    task_type: Mapped[str] = mapped_column(String, default="public_static_refresh")
    endpoint: Mapped[str] = mapped_column(String, nullable=False)
    method: Mapped[str] = mapped_column(String, default="GET")
    params_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    params_json: Mapped[dict] = mapped_column(JSON, default=dict)
    priority: Mapped[str] = mapped_column(String, default="P3_PUBLIC_STATIC")
    status: Mapped[str] = mapped_column(String, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    account_id: Mapped[str | None] = mapped_column(String, nullable=True)
    feature_scope: Mapped[str | None] = mapped_column(String, nullable=True)
    retry_after_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String, nullable=True)
    last_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApiKeySecretModel(Base):
    __tablename__ = "api_key_secrets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    masked_key: Mapped[str] = mapped_column(String, nullable=False)
    storage: Mapped[str] = mapped_column(String, default="sqlite_fernet")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
