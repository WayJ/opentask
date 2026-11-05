"""notification_preferences + comment_reactions (E27)

Revision ID: f6a7b8c9d0e4
Revises: e5f6a7b8c9d3
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e4"
down_revision: Union[str, None] = "e5f6a7b8c9d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "notification_preferences" not in tables:
        op.create_table(
            "notification_preferences",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("issue_assigned", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("issue_comment", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("issue_mention", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("issue_status", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("due_date_changed", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("issue_watch_event", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("automation_comment", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "workspace_id", name="uq_notif_prefs_user_ws"),
        )
        op.create_index(
            "idx_notif_prefs_ws_user",
            "notification_preferences",
            ["workspace_id", "user_id"],
        )
        op.create_index(
            "ix_notification_preferences_user_id",
            "notification_preferences",
            ["user_id"],
        )
        op.create_index(
            "ix_notification_preferences_workspace_id",
            "notification_preferences",
            ["workspace_id"],
        )

    if "comment_reactions" not in tables:
        op.create_table(
            "comment_reactions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "comment_id",
                sa.String(36),
                sa.ForeignKey("issue_comments.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("emoji", sa.String(10), nullable=False),
            sa.Column("user_id", sa.String(255), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("idx_comment_reactions_comment", "comment_reactions", ["comment_id"])
        op.create_index("idx_comment_reactions_emoji", "comment_reactions", ["emoji"])
        op.create_index("idx_comment_reactions_user", "comment_reactions", ["user_id"])
        op.create_index(
            "idx_comment_reactions_comment_emoji",
            "comment_reactions",
            ["comment_id", "emoji"],
        )
        op.create_index(
            "uq_comment_reaction",
            "comment_reactions",
            ["comment_id", "emoji", "user_id"],
            unique=True,
        )
        op.create_index(
            "ix_comment_reactions_comment_id",
            "comment_reactions",
            ["comment_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "comment_reactions" in tables:
        op.drop_table("comment_reactions")
    if "notification_preferences" in tables:
        op.drop_table("notification_preferences")
