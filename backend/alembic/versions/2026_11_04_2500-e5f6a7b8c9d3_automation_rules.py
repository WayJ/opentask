"""automation_rules (E26)

Revision ID: e5f6a7b8c9d3
Revises: d4e5f6a7b8c2
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d3"
down_revision: Union[str, None] = "d4e5f6a7b8c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "automation_rules" not in tables:
        op.create_table(
            "automation_rules",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("trigger_type", sa.String(64), nullable=False),
            sa.Column("trigger_config_json", sa.JSON(), nullable=False),
            sa.Column("condition_json", sa.JSON(), nullable=True),
            sa.Column("action_type", sa.String(64), nullable=False),
            sa.Column("action_config_json", sa.JSON(), nullable=False),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "idx_automation_rules_ws_enabled",
            "automation_rules",
            ["workspace_id", "enabled"],
        )
        op.create_index(
            "idx_automation_rules_ws_trigger",
            "automation_rules",
            ["workspace_id", "trigger_type"],
        )
        op.create_index(
            "idx_automation_rules_ws_position",
            "automation_rules",
            ["workspace_id", "position"],
        )
        op.create_index(
            "ix_automation_rules_workspace_id",
            "automation_rules",
            ["workspace_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "automation_rules" in tables:
        op.drop_table("automation_rules")
