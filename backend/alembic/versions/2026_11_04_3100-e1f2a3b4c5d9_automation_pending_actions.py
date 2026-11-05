"""automation_pending_actions (E38)

Revision ID: e1f2a3b4c5d9
Revises: d0e1f2a3b4c8
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d9"
down_revision: Union[str, None] = "d0e1f2a3b4c8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "automation_pending_actions" not in tables:
        op.create_table(
            "automation_pending_actions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "rule_id",
                sa.String(36),
                sa.ForeignKey("automation_rules.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "issue_id",
                sa.String(36),
                sa.ForeignKey("issues.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("action_type", sa.String(64), nullable=False),
            sa.Column("action_config_json", sa.JSON(), nullable=False),
            sa.Column("run_at", sa.DateTime(), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("actor_user_id", sa.String(36), nullable=True),
            sa.Column("error_message", sa.String(1000), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("executed_at", sa.DateTime(), nullable=True),
        )
        op.create_index(
            "ix_automation_pending_actions_workspace_id",
            "automation_pending_actions",
            ["workspace_id"],
        )
        op.create_index(
            "ix_automation_pending_actions_rule_id",
            "automation_pending_actions",
            ["rule_id"],
        )
        op.create_index(
            "ix_automation_pending_actions_issue_id",
            "automation_pending_actions",
            ["issue_id"],
        )
        op.create_index(
            "idx_auto_pending_ws_status_run",
            "automation_pending_actions",
            ["workspace_id", "status", "run_at"],
        )
        op.create_index(
            "idx_auto_pending_rule_issue_status",
            "automation_pending_actions",
            ["rule_id", "issue_id", "status"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "automation_pending_actions" in tables:
        op.drop_table("automation_pending_actions")
