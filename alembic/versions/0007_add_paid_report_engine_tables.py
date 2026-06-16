"""add paid report engine tables

Revision ID: 0007_add_paid_report_engine_tables
Revises: 0006_add_secret_store_table
Create Date: 2026-06-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0007_add_paid_report_engine_tables"
down_revision: str | None = "0006_add_secret_store_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "report_products",
        sa.Column("product_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("report_type", sa.String(), nullable=False),
        sa.Column("tier", sa.String(), nullable=False),
        sa.Column("price_cents", sa.Integer(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_report_products_report_type", "report_products", ["report_type"])
    op.create_index("ix_report_products_tier", "report_products", ["tier"])

    op.create_table(
        "report_entitlements",
        sa.Column("entitlement_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("product_id", sa.String(), nullable=False),
        sa.Column("entitlement_type", sa.String(), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_report_entitlements_user_id", "report_entitlements", ["user_id"])
    op.create_index("ix_report_entitlements_product_id", "report_entitlements", ["product_id"])

    op.create_table(
        "report_export_jobs",
        sa.Column("job_id", sa.String(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("report_type", sa.String(), nullable=False),
        sa.Column("export_format", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("artifact_path", sa.String(), nullable=True),
        sa.Column("manifest_path", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_report_export_jobs_user_id", "report_export_jobs", ["user_id"])
    op.create_index("ix_report_export_jobs_status", "report_export_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_report_export_jobs_status", table_name="report_export_jobs")
    op.drop_index("ix_report_export_jobs_user_id", table_name="report_export_jobs")
    op.drop_table("report_export_jobs")
    op.drop_index("ix_report_entitlements_product_id", table_name="report_entitlements")
    op.drop_index("ix_report_entitlements_user_id", table_name="report_entitlements")
    op.drop_table("report_entitlements")
    op.drop_index("ix_report_products_tier", table_name="report_products")
    op.drop_index("ix_report_products_report_type", table_name="report_products")
    op.drop_table("report_products")
