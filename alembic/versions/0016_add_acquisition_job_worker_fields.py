"""add acquisition job worker fields

Revision ID: 0016_add_acquisition_job_worker_fields
Revises: 0015_add_acquisition_core_tables
Create Date: 2026-06-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0016_add_acquisition_job_worker_fields"
down_revision: str | None = "0015_add_acquisition_core_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("acquisition_jobs", sa.Column("worker_id", sa.String(), nullable=True))
    op.add_column("acquisition_jobs", sa.Column("leased_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("acquisition_jobs", sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("acquisition_jobs", "next_attempt_at")
    op.drop_column("acquisition_jobs", "leased_until")
    op.drop_column("acquisition_jobs", "worker_id")
