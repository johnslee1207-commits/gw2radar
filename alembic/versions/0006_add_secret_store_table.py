"""add secret store table

Revision ID: 0006_add_secret_store_table
Revises: 0005_expand_refresh_queue_contract
Create Date: 2026-06-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision: str = "0006_add_secret_store_table"
down_revision: str | None = "0005_expand_refresh_queue_contract"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "secrets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("secret_type", sa.String(), nullable=False),
        sa.Column("key_fingerprint", sa.String(), nullable=False),
        sa.Column("encrypted_payload_json", sqlite.JSON(), nullable=False),
        sa.Column("storage_backend", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_secrets_user_id", "secrets", ["user_id"])
    op.create_index("ix_secrets_key_fingerprint", "secrets", ["key_fingerprint"])


def downgrade() -> None:
    op.drop_index("ix_secrets_key_fingerprint", table_name="secrets")
    op.drop_index("ix_secrets_user_id", table_name="secrets")
    op.drop_table("secrets")
