"""activity_read_cursors (E52 thin bell)

Revision ID: n0c1d2e3f4a8
Revises: m9b0c1d2e3f7
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n0c1d2e3f4a8"
down_revision: Union[str, None] = "m9b0c1d2e3f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "activity_read_cursors" in tables:
        return
    op.create_table(
        "activity_read_cursors",
        sa.Column("user_id", sa.String(36), primary_key=True, nullable=False),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.Column("last_seen_id", sa.String(36), nullable=False, server_default=""),
    )
    op.create_index(
        "ix_activity_read_cursors_workspace_id",
        "activity_read_cursors",
        ["workspace_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "activity_read_cursors" not in tables:
        return
    op.drop_index("ix_activity_read_cursors_workspace_id", table_name="activity_read_cursors")
    op.drop_table("activity_read_cursors")
