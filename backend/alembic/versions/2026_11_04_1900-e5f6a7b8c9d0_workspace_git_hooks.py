"""workspace git status hooks settings (E11-S3)

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("workspaces")} if "workspaces" in inspector.get_table_names() else set()
    if "git_status_hooks_enabled" not in cols:
        op.add_column(
            "workspaces",
            sa.Column(
                "git_status_hooks_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="PR webhook may auto-update Issue status",
            ),
        )
    if "git_hook_on_pr_open" not in cols:
        op.add_column(
            "workspaces",
            sa.Column(
                "git_hook_on_pr_open",
                sa.String(32),
                nullable=False,
                server_default="in_progress",
                comment="Target Issue status when PR opens",
            ),
        )
    if "git_hook_on_pr_merged" not in cols:
        op.add_column(
            "workspaces",
            sa.Column(
                "git_hook_on_pr_merged",
                sa.String(32),
                nullable=False,
                server_default="resolved",
                comment="Target Issue status when PR merges",
            ),
        )


def downgrade() -> None:
    op.drop_column("workspaces", "git_hook_on_pr_merged")
    op.drop_column("workspaces", "git_hook_on_pr_open")
    op.drop_column("workspaces", "git_status_hooks_enabled")
