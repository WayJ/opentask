"""notification_preferences.email_enabled (E30)

Revision ID: b8c9d0e1f2a6
Revises: a7b8c9d0e1f5
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a6"
down_revision: Union[str, None] = "a7b8c9d0e1f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "notification_preferences" not in tables:
        return
    cols = {c["name"] for c in inspector.get_columns("notification_preferences")}
    if "email_enabled" not in cols:
        op.add_column(
            "notification_preferences",
            sa.Column(
                "email_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "notification_preferences" not in tables:
        return
    cols = {c["name"] for c in inspector.get_columns("notification_preferences")}
    if "email_enabled" in cols:
        op.drop_column("notification_preferences", "email_enabled")
