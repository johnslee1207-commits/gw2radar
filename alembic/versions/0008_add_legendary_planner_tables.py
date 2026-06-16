"""add legendary planner pro tables

Revision ID: 0008_add_legendary_planner_tables
Revises: 0007_add_paid_report_engine_tables
Create Date: 2026-06-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0008_add_legendary_planner_tables"
down_revision: str | None = "0007_add_paid_report_engine_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "goal_portfolios",
        sa.Column("portfolio_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_goal_portfolios_user_id", "goal_portfolios", ["user_id"])

    op.create_table(
        "legendary_goals",
        sa.Column("goal_record_id", sa.String(), primary_key=True),
        sa.Column("portfolio_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("graph_goal_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_legendary_goals_portfolio_id", "legendary_goals", ["portfolio_id"])
    op.create_index("ix_legendary_goals_user_id", "legendary_goals", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_legendary_goals_user_id", table_name="legendary_goals")
    op.drop_index("ix_legendary_goals_portfolio_id", table_name="legendary_goals")
    op.drop_table("legendary_goals")
    op.drop_index("ix_goal_portfolios_user_id", table_name="goal_portfolios")
    op.drop_table("goal_portfolios")
