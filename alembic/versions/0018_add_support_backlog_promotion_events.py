"""add support backlog promotion events

Revision ID: 0018_add_support_backlog_promotion_events
Revises: 0017_add_support_backlog_promotions
Create Date: 2026-06-19
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0018_add_support_backlog_promotion_events"
down_revision: str | None = "0017_add_support_backlog_promotions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "support_backlog_promotion_events",
        sa.Column("event_id", sa.String(), primary_key=True),
        sa.Column("promotion_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("previous_status", sa.String(), nullable=True),
        sa.Column("new_status", sa.String(), nullable=True),
        sa.Column("reviewer", sa.String(), nullable=False, server_default="support"),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("properties_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("support_backlog_promotion_events")
