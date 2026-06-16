"""add refresh queue and api key secrets

Revision ID: 0004_add_refresh_queue_and_api_key_secrets
Revises: 0003_add_graph_layer_fields
Create Date: 2026-06-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision: str = "0004_add_refresh_queue_and_api_key_secrets"
down_revision: str | None = "0003_add_graph_layer_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "refresh_queue",
        sa.Column("request_id", sa.String(), primary_key=True),
        sa.Column("endpoint", sa.String(), nullable=False),
        sa.Column("params_json", sqlite.JSON(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False, server_default="P3"),
        sa.Column("status", sa.String(), nullable=False, server_default="queued"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_after_seconds", sa.Integer(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "api_key_secrets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("masked_key", sa.String(), nullable=False),
        sa.Column("storage", sa.String(), nullable=False, server_default="sqlite_fernet"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("api_key_secrets")
    op.drop_table("refresh_queue")
