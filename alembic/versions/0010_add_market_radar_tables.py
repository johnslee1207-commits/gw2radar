"""add market radar tables

Revision ID: 0010_add_market_radar_tables
Revises: 0009_add_build_fit_tables
Create Date: 2026-06-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0010_add_market_radar_tables"
down_revision: str | None = "0009_add_build_fit_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "market_snapshots",
        sa.Column("snapshot_id", sa.String(), primary_key=True),
        sa.Column("item_id", sa.String(), nullable=False),
        sa.Column("item_name", sa.String(), nullable=False),
        sa.Column("buy_price_copper", sa.Integer(), nullable=False),
        sa.Column("sell_price_copper", sa.Integer(), nullable=False),
        sa.Column("volume", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_market_snapshots_item_id", "market_snapshots", ["item_id"])
    op.create_index("ix_market_snapshots_observed_at", "market_snapshots", ["observed_at"])

    op.create_table(
        "market_watchlist",
        sa.Column("watch_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("item_id", sa.String(), nullable=False),
        sa.Column("item_name", sa.String(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_market_watchlist_user_id", "market_watchlist", ["user_id"])
    op.create_index("ix_market_watchlist_item_id", "market_watchlist", ["item_id"])


def downgrade() -> None:
    op.drop_index("ix_market_watchlist_item_id", table_name="market_watchlist")
    op.drop_index("ix_market_watchlist_user_id", table_name="market_watchlist")
    op.drop_table("market_watchlist")
    op.drop_index("ix_market_snapshots_observed_at", table_name="market_snapshots")
    op.drop_index("ix_market_snapshots_item_id", table_name="market_snapshots")
    op.drop_table("market_snapshots")
