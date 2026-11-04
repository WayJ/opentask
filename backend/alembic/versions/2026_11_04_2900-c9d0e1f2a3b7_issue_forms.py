"""issue_forms (E31)

Revision ID: c9d0e1f2a3b7
Revises: b8c9d0e1f2a6
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b7"
down_revision: Union[str, None] = "b8c9d0e1f2a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "issue_forms" not in tables:
        op.create_table(
            "issue_forms",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("slug", sa.String(80), nullable=True),
            sa.Column("token", sa.String(64), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("fields_json", sa.JSON(), nullable=False),
            sa.Column(
                "create_customer_request",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("token", name="uq_issue_forms_token"),
            sa.UniqueConstraint("workspace_id", "slug", name="uq_issue_forms_ws_slug"),
        )
        op.create_index("ix_issue_forms_workspace_id", "issue_forms", ["workspace_id"])
        op.create_index("ix_issue_forms_token", "issue_forms", ["token"])
        op.create_index(
            "idx_issue_forms_ws_enabled",
            "issue_forms",
            ["workspace_id", "enabled"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_forms" in tables:
        op.drop_table("issue_forms")
