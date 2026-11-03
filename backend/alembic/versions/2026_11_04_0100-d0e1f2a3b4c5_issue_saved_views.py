"""issue_saved_views 表（E4-S1 Saved Views）

Revision ID: d0e1f2a3b4c5
Revises: c9d8e7f6a5b4
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d8e7f6a5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "issue_saved_views" not in tables:
        op.create_table(
            "issue_saved_views",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("owner_user_id", sa.String(36), nullable=False),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("filter_json", sa.JSON(), nullable=False),
            sa.Column("sort_json", sa.JSON(), nullable=True),
            sa.Column("display_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_issue_saved_views_workspace_id", "issue_saved_views", ["workspace_id"])
        op.create_index("ix_issue_saved_views_owner_user_id", "issue_saved_views", ["owner_user_id"])
        op.create_index(
            "idx_saved_views_ws_owner",
            "issue_saved_views",
            ["workspace_id", "owner_user_id"],
        )
        op.create_index(
            "idx_saved_views_owner_fav",
            "issue_saved_views",
            ["owner_user_id", "is_favorite"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_saved_views" in tables:
        op.drop_index("idx_saved_views_owner_fav", table_name="issue_saved_views")
        op.drop_index("idx_saved_views_ws_owner", table_name="issue_saved_views")
        op.drop_index("ix_issue_saved_views_owner_user_id", table_name="issue_saved_views")
        op.drop_index("ix_issue_saved_views_workspace_id", table_name="issue_saved_views")
        op.drop_table("issue_saved_views")
