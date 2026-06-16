"""add evidence governance fields

Revision ID: 0002_add_evidence_governance_fields
Revises: 0001_create_mvp_tables
Create Date: 2026-06-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002_add_evidence_governance_fields"
down_revision: str | None = "0001_create_mvp_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evidence", sa.Column("source_type", sa.String(), nullable=False, server_default="mock"))
    op.add_column("evidence", sa.Column("payload_ref", sa.String(), nullable=True))
    op.add_column("evidence", sa.Column("license_note", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("evidence", "license_note")
    op.drop_column("evidence", "payload_ref")
    op.drop_column("evidence", "source_type")
