"""Inbox notifications 表（E3-S3）

Revision ID: c9d8e7f6a5b4
Revises: a1b2c3d4e5f6
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d8e7f6a5b4"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "notifications" not in tables:
        op.create_table(
            "notifications",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("recipient_user_id", sa.String(36), nullable=False),
            sa.Column("actor_user_id", sa.String(36), nullable=True),
            sa.Column("type", sa.String(32), nullable=False),
            sa.Column("resource_type", sa.String(32), nullable=False),
            sa.Column("resource_id", sa.String(36), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("body", sa.Text(), nullable=True),
            sa.Column("read_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_notifications_workspace_id", "notifications", ["workspace_id"])
        op.create_index("ix_notifications_recipient_user_id", "notifications", ["recipient_user_id"])
        op.create_index("ix_notifications_resource_id", "notifications", ["resource_id"])
        op.create_index(
            "idx_notifications_recipient_created",
            "notifications",
            ["recipient_user_id", "created_at"],
        )
        op.create_index(
            "idx_notifications_ws_recipient",
            "notifications",
            ["workspace_id", "recipient_user_id"],
        )
        op.create_index(
            "idx_notifications_recipient_unread",
            "notifications",
            ["recipient_user_id", "read_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "notifications" in tables:
        op.drop_index("idx_notifications_recipient_unread", table_name="notifications")
        op.drop_index("idx_notifications_ws_recipient", table_name="notifications")
        op.drop_index("idx_notifications_recipient_created", table_name="notifications")
        op.drop_index("ix_notifications_resource_id", table_name="notifications")
        op.drop_index("ix_notifications_recipient_user_id", table_name="notifications")
        op.drop_index("ix_notifications_workspace_id", table_name="notifications")
        op.drop_table("notifications")
