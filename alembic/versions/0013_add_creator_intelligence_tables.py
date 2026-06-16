"""add creator intelligence tables

Revision ID: 0013_add_creator_intelligence_tables
Revises: 0012_add_guild_readiness_tables
Create Date: 2026-06-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0013_add_creator_intelligence_tables"
down_revision: str | None = "0012_add_guild_readiness_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "community_signals",
        sa.Column("signal_id", sa.String(), primary_key=True),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(), nullable=False),
        sa.Column("audience_segment", sa.String(), nullable=False),
        sa.Column("signal_kind", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("authorized_source", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_community_signals_topic", "community_signals", ["topic"])
    op.create_index("ix_community_signals_source_type", "community_signals", ["source_type"])


def downgrade() -> None:
    op.drop_index("ix_community_signals_source_type", table_name="community_signals")
    op.drop_index("ix_community_signals_topic", table_name="community_signals")
    op.drop_table("community_signals")
