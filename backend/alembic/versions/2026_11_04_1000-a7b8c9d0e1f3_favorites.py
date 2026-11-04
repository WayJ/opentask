"""favorites polymorphic sidebar pins (E8-S3)

Revision ID: a7b8c9d0e1f3
Revises: f6a7b8c9d0e2
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f3"
down_revision: Union[str, None] = "f6a7b8c9d0e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "favorites" not in tables:
        op.create_table(
            "favorites",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("workspace_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("target_type", sa.String(20), nullable=False),
            sa.Column("target_id", sa.String(36), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.UniqueConstraint(
                "workspace_id",
                "user_id",
                "target_type",
                "target_id",
                name="uq_favorites_user_target",
            ),
        )
        op.create_index("ix_favorites_workspace_id", "favorites", ["workspace_id"])
        op.create_index("ix_favorites_user_id", "favorites", ["user_id"])
        op.create_index(
            "ix_favorites_user_ws_pos",
            "favorites",
            ["user_id", "workspace_id", "position"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "favorites" in tables:
        op.drop_table("favorites")
