"""issue_vcs_links for E11-S1 branch/PR links on Issue

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_vcs_links" not in tables:
        op.create_table(
            "issue_vcs_links",
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
            sa.Column("kind", sa.String(32), nullable=False),
            sa.Column("branch_name", sa.String(255), nullable=True),
            sa.Column("pr_url", sa.String(500), nullable=True),
            sa.Column("provider", sa.String(32), nullable=False, server_default="manual"),
            sa.Column("external_id", sa.String(100), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="unknown"),
            sa.Column(
                "repo_config_id",
                sa.Integer(),
                sa.ForeignKey("repo_configs.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("title", sa.String(255), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_issue_vcs_links_workspace_id", "issue_vcs_links", ["workspace_id"])
        op.create_index("ix_issue_vcs_links_issue_id", "issue_vcs_links", ["issue_id"])
        op.create_index(
            "idx_issue_vcs_links_issue_kind",
            "issue_vcs_links",
            ["issue_id", "kind"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "issue_vcs_links" in set(inspector.get_table_names()):
        op.drop_table("issue_vcs_links")
