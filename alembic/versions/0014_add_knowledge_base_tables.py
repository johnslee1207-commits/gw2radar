"""add knowledge base tables

Revision ID: 0014_add_knowledge_base_tables
Revises: 0013_add_creator_intelligence_tables
Create Date: 2026-06-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

revision: str = "0014_add_knowledge_base_tables"
down_revision: str | None = "0013_add_creator_intelligence_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_sources",
        sa.Column("source_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=True),
        sa.Column("allowed_use", sa.String(), nullable=False),
        sa.Column("crawl_policy", sa.String(), nullable=False),
        sa.Column("rate_limit_policy", sa.String(), nullable=False),
        sa.Column("license_note", sa.Text(), nullable=True),
        sa.Column("default_confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_knowledge_sources_source_type", "knowledge_sources", ["source_type"])

    op.create_table(
        "knowledge_articles",
        sa.Column("kb_id", sa.String(), primary_key=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("content_type", sa.String(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("source_refs_json", sqlite.JSON(), nullable=False),
        sa.Column("linked_entities_json", sqlite.JSON(), nullable=False),
        sa.Column("linked_relations_json", sqlite.JSON(), nullable=False),
        sa.Column("linked_actions_json", sqlite.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("review_status", sa.String(), nullable=False),
        sa.Column("last_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_knowledge_articles_domain", "knowledge_articles", ["domain"])
    op.create_index("ix_knowledge_articles_review_status", "knowledge_articles", ["review_status"])

    op.create_table(
        "knowledge_chunks",
        sa.Column("chunk_id", sa.String(), primary_key=True),
        sa.Column("kb_id", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding_id", sa.String(), nullable=True),
        sa.Column("linked_entities_json", sqlite.JSON(), nullable=False),
        sa.Column("linked_actions_json", sqlite.JSON(), nullable=False),
        sa.Column("source_refs_json", sqlite.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_knowledge_chunks_kb_id", "knowledge_chunks", ["kb_id"])

    op.create_table(
        "knowledge_rules",
        sa.Column("rule_id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("condition", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("priority_delta", sa.Float(), nullable=False),
        sa.Column("explanation_template", sa.Text(), nullable=False),
        sa.Column("evidence_refs_json", sqlite.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("review_status", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_knowledge_rules_domain", "knowledge_rules", ["domain"])
    op.create_index("ix_knowledge_rules_review_status", "knowledge_rules", ["review_status"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_rules_review_status", table_name="knowledge_rules")
    op.drop_index("ix_knowledge_rules_domain", table_name="knowledge_rules")
    op.drop_table("knowledge_rules")
    op.drop_index("ix_knowledge_chunks_kb_id", table_name="knowledge_chunks")
    op.drop_table("knowledge_chunks")
    op.drop_index("ix_knowledge_articles_review_status", table_name="knowledge_articles")
    op.drop_index("ix_knowledge_articles_domain", table_name="knowledge_articles")
    op.drop_table("knowledge_articles")
    op.drop_index("ix_knowledge_sources_source_type", table_name="knowledge_sources")
    op.drop_table("knowledge_sources")
