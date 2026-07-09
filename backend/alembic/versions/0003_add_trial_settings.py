"""add trial_settings table

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trial_settings",
        sa.Column("trial_id", UUID(as_uuid=True), sa.ForeignKey("trials.id"), primary_key=True),
        sa.Column("llm_model", sa.String(255), nullable=True),
        sa.Column("top_k_retrieval", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("top_n_rerank", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("chunk_size", sa.Integer(), nullable=False, server_default="1000"),
        sa.Column("chunk_overlap", sa.Integer(), nullable=False, server_default="200"),
        sa.Column("cohere_rerank_model", sa.String(255), nullable=True),
        sa.Column("evaluation_threshold", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("trial_settings")
