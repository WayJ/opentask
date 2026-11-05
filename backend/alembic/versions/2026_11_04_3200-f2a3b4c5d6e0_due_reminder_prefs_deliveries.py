"""due_reminder prefs + due_reminder_deliveries (E39)

Revision ID: f2a3b4c5d6e0
Revises: e1f2a3b4c5d9
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a3b4c5d6e0"
down_revision: Union[str, None] = "e1f2a3b4c5d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "notification_preferences" in tables:
        cols = {c["name"] for c in inspector.get_columns("notification_preferences")}
        if "due_reminder" not in cols:
            op.add_column(
                "notification_preferences",
                sa.Column(
                    "due_reminder",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                ),
            )
        if "due_reminder_digest" not in cols:
            op.add_column(
                "notification_preferences",
                sa.Column(
                    "due_reminder_digest",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                ),
            )

    if "due_reminder_deliveries" not in tables:
        op.create_table(
            "due_reminder_deliveries",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "issue_id",
                sa.String(36),
                sa.ForeignKey("issues.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("kind", sa.String(16), nullable=False),
            sa.Column("bucket_date", sa.Date(), nullable=False),
            sa.Column("due_date_bucket", sa.Date(), nullable=True),
            sa.Column("dedupe_key", sa.String(160), nullable=False),
            sa.Column("notification_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_due_reminder_deliveries_workspace_id",
            "due_reminder_deliveries",
            ["workspace_id"],
        )
        op.create_index(
            "ix_due_reminder_deliveries_issue_id",
            "due_reminder_deliveries",
            ["issue_id"],
        )
        op.create_index(
            "ix_due_reminder_deliveries_user_id",
            "due_reminder_deliveries",
            ["user_id"],
        )
        op.create_index(
            "idx_due_rem_ws_bucket",
            "due_reminder_deliveries",
            ["workspace_id", "bucket_date"],
        )
        op.create_index(
            "idx_due_rem_user_bucket",
            "due_reminder_deliveries",
            ["user_id", "bucket_date"],
        )
        op.create_index(
            "uq_due_rem_ws_dedupe",
            "due_reminder_deliveries",
            ["workspace_id", "dedupe_key"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "due_reminder_deliveries" in tables:
        op.drop_table("due_reminder_deliveries")
    if "notification_preferences" in tables:
        cols = {c["name"] for c in inspector.get_columns("notification_preferences")}
        if "due_reminder_digest" in cols:
            op.drop_column("notification_preferences", "due_reminder_digest")
        if "due_reminder" in cols:
            op.drop_column("notification_preferences", "due_reminder")
