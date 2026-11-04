"""sla_policies + issue_sla_clocks + sla_breached pref (E42)

Revision ID: i5d6e7f8a9b3
Revises: h4c5d6e7f8a2
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "i5d6e7f8a9b3"
down_revision: Union[str, None] = "h4c5d6e7f8a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "notification_preferences" in tables:
        cols = {c["name"] for c in inspector.get_columns("notification_preferences")}
        if "sla_breached" not in cols:
            op.add_column(
                "notification_preferences",
                sa.Column(
                    "sla_breached",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.true(),
                ),
            )

    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    if "sla_policies" not in tables:
        op.create_table(
            "sla_policies",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(80), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("metric", sa.String(32), nullable=False, server_default="time_in_status"),
            sa.Column("start_statuses", json_type, nullable=False),
            sa.Column("stop_statuses", json_type, nullable=False),
            sa.Column("target_minutes", sa.Integer(), nullable=False, server_default="1440"),
            sa.Column("notify_assignee", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("notify_watchers", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_sla_policies_workspace_id", "sla_policies", ["workspace_id"])
        op.create_index("idx_sla_policies_ws_enabled", "sla_policies", ["workspace_id", "enabled"])

    if "issue_sla_clocks" not in tables:
        op.create_table(
            "issue_sla_clocks",
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
            sa.Column(
                "policy_id",
                sa.String(36),
                sa.ForeignKey("sla_policies.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("deadline_at", sa.DateTime(), nullable=False),
            sa.Column("stopped_at", sa.DateTime(), nullable=True),
            sa.Column("breached_at", sa.DateTime(), nullable=True),
            sa.Column("start_status", sa.String(32), nullable=False),
        )
        op.create_index("ix_issue_sla_clocks_workspace_id", "issue_sla_clocks", ["workspace_id"])
        op.create_index("ix_issue_sla_clocks_issue_id", "issue_sla_clocks", ["issue_id"])
        op.create_index("ix_issue_sla_clocks_policy_id", "issue_sla_clocks", ["policy_id"])
        op.create_index(
            "idx_issue_sla_clocks_ws_status_deadline",
            "issue_sla_clocks",
            ["workspace_id", "status", "deadline_at"],
        )
        op.create_index(
            "idx_issue_sla_clocks_issue_policy",
            "issue_sla_clocks",
            ["issue_id", "policy_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_sla_clocks" in tables:
        op.drop_table("issue_sla_clocks")
    if "sla_policies" in tables:
        op.drop_table("sla_policies")
    if "notification_preferences" in tables:
        cols = {c["name"] for c in inspector.get_columns("notification_preferences")}
        if "sla_breached" in cols:
            op.drop_column("notification_preferences", "sla_breached")
