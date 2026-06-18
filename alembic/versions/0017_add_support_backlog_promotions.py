"""add support backlog promotions

Revision ID: 0017_add_support_backlog_promotions
Revises: 0016_add_acquisition_job_worker_fields
Create Date: 2026-06-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0017_add_support_backlog_promotions"
down_revision: str | None = "0016_add_acquisition_job_worker_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "support_backlog_promotions",
        sa.Column("promotion_id", sa.String(), primary_key=True),
        sa.Column("backlog_id", sa.String(), nullable=False),
        sa.Column("blocker_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("artifact_type", sa.String(), nullable=False, server_default="roadmap_issue_draft"),
        sa.Column("status", sa.String(), nullable=False, server_default="draft"),
        sa.Column("reviewer", sa.String(), nullable=False, server_default="support"),
        sa.Column("source", sa.String(), nullable=False, server_default="support_backlog"),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("properties_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("support_backlog_promotions")
