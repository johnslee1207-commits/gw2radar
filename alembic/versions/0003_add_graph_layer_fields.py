"""add graph layer fields

Revision ID: 0003_add_graph_layer_fields
Revises: 0002_add_evidence_governance_fields
Create Date: 2026-06-16
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_add_graph_layer_fields"
down_revision: str | None = "0002_add_evidence_governance_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("entities", sa.Column("graph_layer", sa.String(), nullable=False, server_default="public_game"))
    op.add_column("relations", sa.Column("graph_layer", sa.String(), nullable=False, server_default="public_game"))
    op.add_column("evidence", sa.Column("graph_layer", sa.String(), nullable=False, server_default="public_game"))
    op.add_column(
        "player_state",
        sa.Column("graph_layer", sa.String(), nullable=False, server_default="private_player_state"),
    )
    op.add_column(
        "actions",
        sa.Column("graph_layer", sa.String(), nullable=False, server_default="personal_intelligence"),
    )


def downgrade() -> None:
    op.drop_column("actions", "graph_layer")
    op.drop_column("player_state", "graph_layer")
    op.drop_column("evidence", "graph_layer")
    op.drop_column("relations", "graph_layer")
    op.drop_column("entities", "graph_layer")
