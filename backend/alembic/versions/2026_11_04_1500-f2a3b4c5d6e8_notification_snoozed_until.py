"""notifications.snoozed_until (E9-S3)

Revision ID: f2a3b4c5d6e8
Revises: e1f2a3b4c5d7
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a3b4c5d6e8"
down_revision: Union[str, None] = "e1f2a3b4c5d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("notifications")}
    if "snoozed_until" not in cols:
        op.add_column(
            "notifications",
            sa.Column("snoozed_until", sa.DateTime(), nullable=True),
        )
    indexes = {i["name"] for i in inspector.get_indexes("notifications")}
    if "idx_notifications_recipient_snoozed" not in indexes:
        op.create_index(
            "idx_notifications_recipient_snoozed",
            "notifications",
            ["recipient_user_id", "snoozed_until"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {i["name"] for i in inspector.get_indexes("notifications")}
    if "idx_notifications_recipient_snoozed" in indexes:
        op.drop_index("idx_notifications_recipient_snoozed", table_name="notifications")
    cols = {c["name"] for c in inspector.get_columns("notifications")}
    if "snoozed_until" in cols:
        op.drop_column("notifications", "snoozed_until")
