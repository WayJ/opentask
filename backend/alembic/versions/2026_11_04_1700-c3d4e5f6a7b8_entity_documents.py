"""entity_documents light MD (E10-S3)

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "entity_documents" not in tables:
        op.create_table(
            "entity_documents",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("parent_type", sa.String(32), nullable=False),
            sa.Column("parent_id", sa.String(36), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("body_md", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "idx_entity_documents_parent",
            "entity_documents",
            ["workspace_id", "parent_type", "parent_id"],
        )
        op.create_index("ix_entity_documents_workspace_id", "entity_documents", ["workspace_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "entity_documents" in set(inspector.get_table_names()):
        op.drop_table("entity_documents")
