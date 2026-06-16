"""add build fit tables

Revision ID: 0009_add_build_fit_tables
Revises: 0008_add_legendary_planner_tables
Create Date: 2026-06-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision: str = "0009_add_build_fit_tables"
down_revision: str | None = "0008_add_legendary_planner_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "builds",
        sa.Column("build_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("source_attribution", sa.String(), nullable=False),
        sa.Column("profession", sa.String(), nullable=False),
        sa.Column("specialization", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("game_mode", sa.String(), nullable=False),
        sa.Column("patch_version", sa.String(), nullable=True),
        sa.Column("patch_freshness_days", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.String(), nullable=False),
        sa.Column("requirements_json", sqlite.JSON(), nullable=False),
        sa.Column("estimated_transition_cost_gold", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_builds_user_id", "builds", ["user_id"])
    op.create_index("ix_builds_profession", "builds", ["profession"])


def downgrade() -> None:
    op.drop_index("ix_builds_profession", table_name="builds")
    op.drop_index("ix_builds_user_id", table_name="builds")
    op.drop_table("builds")
