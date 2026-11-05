"""issue_links + timeline link_added/link_removed (E76)

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, None] = "a4b5c6d7e8f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_links" not in tables:
        op.create_table(
            "issue_links",
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
                nullable=False,
            ),
            sa.Column("url", sa.String(2048), nullable=False),
            sa.Column("title", sa.String(255), nullable=True),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_issue_links_workspace_id", "issue_links", ["workspace_id"])
        op.create_index("ix_issue_links_issue_id", "issue_links", ["issue_id"])
        op.create_index(
            "idx_issue_links_issue_position",
            "issue_links",
            ["issue_id", "position"],
        )
        op.create_index(
            "idx_issue_links_workspace_issue",
            "issue_links",
            ["workspace_id", "issue_id"],
        )

    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TYPE timeline_action ADD VALUE IF NOT EXISTS 'link_added'"
        )
        op.execute(
            "ALTER TYPE timeline_action ADD VALUE IF NOT EXISTS 'link_removed'"
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "issue_links" in set(inspector.get_table_names()):
        op.drop_table("issue_links")
    # PG cannot easily drop enum values; leave as no-op.
