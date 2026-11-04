"""issue_display_prefs（E7-S3 personal display defaults）

Revision ID: d4e5f6a7b8c0
Revises: c3d4e5f6a7b9
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c0"
down_revision: Union[str, None] = "c3d4e5f6a7b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_display_prefs" in tables:
        return

    op.create_table(
        "issue_display_prefs",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("display_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "user_id",
            name="uq_issue_display_prefs_ws_user",
        ),
    )
    op.create_index(
        "ix_issue_display_prefs_workspace_id",
        "issue_display_prefs",
        ["workspace_id"],
    )
    op.create_index(
        "ix_issue_display_prefs_user_id",
        "issue_display_prefs",
        ["user_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_display_prefs" not in tables:
        return
    op.drop_index("ix_issue_display_prefs_user_id", table_name="issue_display_prefs")
    op.drop_index("ix_issue_display_prefs_workspace_id", table_name="issue_display_prefs")
    op.drop_table("issue_display_prefs")
