"""issue_recurrences (E35)

Revision ID: d0e1f2a3b4c8
Revises: c9d0e1f2a3b7
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c8"
down_revision: Union[str, None] = "c9d0e1f2a3b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "issue_recurrences" not in tables:
        op.create_table(
            "issue_recurrences",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("title_template", sa.String(500), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("priority", sa.String(32), nullable=True),
            sa.Column("labels_json", sa.JSON(), nullable=False),
            sa.Column("project_id", sa.String(36), nullable=True),
            sa.Column("assignee_id", sa.String(36), nullable=True),
            sa.Column("custom_fields_json", sa.JSON(), nullable=False),
            sa.Column("interval", sa.String(16), nullable=False),
            sa.Column("weekday", sa.Integer(), nullable=True),
            sa.Column("monthday", sa.Integer(), nullable=True),
            sa.Column("next_run_at", sa.DateTime(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("last_issue_id", sa.String(36), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "ix_issue_recurrences_workspace_id", "issue_recurrences", ["workspace_id"]
        )
        op.create_index(
            "idx_issue_recurrences_ws_enabled",
            "issue_recurrences",
            ["workspace_id", "enabled"],
        )
        op.create_index(
            "idx_issue_recurrences_ws_next",
            "issue_recurrences",
            ["workspace_id", "next_run_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_recurrences" in tables:
        op.drop_table("issue_recurrences")
