"""expand refresh queue contract

Revision ID: 0005_expand_refresh_queue_contract
Revises: 0004_add_refresh_queue_and_api_key_secrets
Create Date: 2026-06-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0005_expand_refresh_queue_contract"
down_revision: str | None = "0004_add_refresh_queue_and_api_key_secrets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("refresh_queue", sa.Column("task_type", sa.String(), nullable=False, server_default="public_static_refresh"))
    op.add_column("refresh_queue", sa.Column("method", sa.String(), nullable=False, server_default="GET"))
    op.add_column("refresh_queue", sa.Column("params_hash", sa.String(), nullable=True))
    op.add_column("refresh_queue", sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"))
    op.add_column("refresh_queue", sa.Column("account_id", sa.String(), nullable=True))
    op.add_column("refresh_queue", sa.Column("feature_scope", sa.String(), nullable=True))
    op.add_column("refresh_queue", sa.Column("leased_until", sa.DateTime(timezone=True), nullable=True))
    op.add_column("refresh_queue", sa.Column("worker_id", sa.String(), nullable=True))
    op.add_column("refresh_queue", sa.Column("last_status_code", sa.Integer(), nullable=True))
    op.add_column("refresh_queue", sa.Column("last_error_code", sa.String(), nullable=True))
    op.add_column("refresh_queue", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("refresh_queue", "completed_at")
    op.drop_column("refresh_queue", "last_error_code")
    op.drop_column("refresh_queue", "last_status_code")
    op.drop_column("refresh_queue", "worker_id")
    op.drop_column("refresh_queue", "leased_until")
    op.drop_column("refresh_queue", "feature_scope")
    op.drop_column("refresh_queue", "account_id")
    op.drop_column("refresh_queue", "max_attempts")
    op.drop_column("refresh_queue", "params_hash")
    op.drop_column("refresh_queue", "method")
    op.drop_column("refresh_queue", "task_type")
