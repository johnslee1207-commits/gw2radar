"""add guild readiness tables

Revision ID: 0012_add_guild_readiness_tables
Revises: 0011_add_growth_payment_tables
Create Date: 2026-06-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision: str = "0012_add_guild_readiness_tables"
down_revision: str | None = "0011_add_growth_payment_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "guilds",
        sa.Column("guild_id", sa.String(), primary_key=True),
        sa.Column("owner_user_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_guilds_owner_user_id", "guilds", ["owner_user_id"])

    op.create_table(
        "teams",
        sa.Column("team_id", sa.String(), primary_key=True),
        sa.Column("guild_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("game_mode", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_teams_guild_id", "teams", ["guild_id"])

    op.create_table(
        "team_members",
        sa.Column("member_id", sa.String(), primary_key=True),
        sa.Column("team_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("preferred_roles_json", sqlite.JSON(), nullable=False),
        sa.Column("readiness_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_team_members_team_id", "team_members", ["team_id"])

    op.create_table(
        "consent_records",
        sa.Column("consent_id", sa.String(), primary_key=True),
        sa.Column("team_id", sa.String(), nullable=False),
        sa.Column("member_id", sa.String(), nullable=False),
        sa.Column("consent_scope", sa.String(), nullable=False),
        sa.Column("granted", sa.Boolean(), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_consent_records_member_id", "consent_records", ["member_id"])
    op.create_index("ix_consent_records_team_id", "consent_records", ["team_id"])


def downgrade() -> None:
    op.drop_index("ix_consent_records_team_id", table_name="consent_records")
    op.drop_index("ix_consent_records_member_id", table_name="consent_records")
    op.drop_table("consent_records")
    op.drop_index("ix_team_members_team_id", table_name="team_members")
    op.drop_table("team_members")
    op.drop_index("ix_teams_guild_id", table_name="teams")
    op.drop_table("teams")
    op.drop_index("ix_guilds_owner_user_id", table_name="guilds")
    op.drop_table("guilds")
