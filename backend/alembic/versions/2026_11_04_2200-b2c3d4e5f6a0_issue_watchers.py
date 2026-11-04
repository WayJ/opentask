"""issue_watchers for Inbox fanout (E18)

Revision ID: b2c3d4e5f6a0
Revises: a1b2c3d4e5f9
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a0"
down_revision: Union[str, None] = "a1b2c3d4e5f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_watchers" not in tables:
        op.create_table(
            "issue_watchers",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("workspace_id", sa.String(36), nullable=False),
            sa.Column("issue_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("issue_id", "user_id", name="uq_issue_watchers_issue_user"),
        )
        op.create_index("ix_issue_watchers_workspace_id", "issue_watchers", ["workspace_id"])
        op.create_index("ix_issue_watchers_issue_id", "issue_watchers", ["issue_id"])
        op.create_index("ix_issue_watchers_user_id", "issue_watchers", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_watchers" in tables:
        op.drop_table("issue_watchers")
