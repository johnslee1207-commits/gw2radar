"""add acquisition core tables

Revision ID: 0015_add_acquisition_core_tables
Revises: 0014_add_knowledge_base_tables
Create Date: 2026-06-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision: str = "0015_add_acquisition_core_tables"
down_revision: str | None = "0014_add_knowledge_base_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "acquisition_sources",
        sa.Column("source_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("acquisition_mode", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=True),
        sa.Column("local_path", sa.String(), nullable=True),
        sa.Column("allowed_use", sa.String(), nullable=False),
        sa.Column("graph_target", sa.String(), nullable=False),
        sa.Column("kb_target", sa.String(), nullable=False),
        sa.Column("trust_level", sa.Float(), nullable=False),
        sa.Column("review_required", sa.Boolean(), nullable=False),
        sa.Column("review_status", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_acquisition_sources_source_type", "acquisition_sources", ["source_type"])
    op.create_index("ix_acquisition_sources_kb_target", "acquisition_sources", ["kb_target"])

    op.create_table(
        "source_policies",
        sa.Column("policy_id", sa.String(), primary_key=True),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("allowed_use", sa.String(), nullable=False),
        sa.Column("refresh_mode", sa.String(), nullable=False),
        sa.Column("refresh_interval_seconds", sa.Integer(), nullable=True),
        sa.Column("freshness_required_for_strong_action", sa.Boolean(), nullable=False),
        sa.Column("can_drive_paid_report", sa.Boolean(), nullable=False),
        sa.Column("can_drive_strong_recommendation", sa.Boolean(), nullable=False),
        sa.Column("retain_raw_evidence", sa.Boolean(), nullable=False),
        sa.Column("forbidden_use_json", sqlite.JSON(), nullable=False),
        sa.Column("attribution_required", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_source_policies_source_id", "source_policies", ["source_id"])

    op.create_table(
        "acquisition_jobs",
        sa.Column("job_id", sa.String(), primary_key=True),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("params_json", sqlite.JSON(), nullable=False),
        sa.Column("requested_by", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("last_error_code", sa.String(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_acquisition_jobs_source_id", "acquisition_jobs", ["source_id"])
    op.create_index("ix_acquisition_jobs_status", "acquisition_jobs", ["status"])

    op.create_table(
        "raw_evidence",
        sa.Column("evidence_id", sa.String(), primary_key=True),
        sa.Column("source_id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), nullable=True),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("payload_ref", sa.String(), nullable=True),
        sa.Column("payload_hash", sa.String(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("metadata_json", sqlite.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_raw_evidence_source_id", "raw_evidence", ["source_id"])
    op.create_index("ix_raw_evidence_job_id", "raw_evidence", ["job_id"])


def downgrade() -> None:
    op.drop_index("ix_raw_evidence_job_id", table_name="raw_evidence")
    op.drop_index("ix_raw_evidence_source_id", table_name="raw_evidence")
    op.drop_table("raw_evidence")
    op.drop_index("ix_acquisition_jobs_status", table_name="acquisition_jobs")
    op.drop_index("ix_acquisition_jobs_source_id", table_name="acquisition_jobs")
    op.drop_table("acquisition_jobs")
    op.drop_index("ix_source_policies_source_id", table_name="source_policies")
    op.drop_table("source_policies")
    op.drop_index("ix_acquisition_sources_kb_target", table_name="acquisition_sources")
    op.drop_index("ix_acquisition_sources_source_type", table_name="acquisition_sources")
    op.drop_table("acquisition_sources")
