"""workspace_webhooks + webhook_delivery_logs (E29)

Revision ID: a7b8c9d0e1f5
Revises: f6a7b8c9d0e4
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7b8c9d0e1f5"
down_revision: Union[str, None] = "f6a7b8c9d0e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "workspace_webhooks" not in tables:
        op.create_table(
            "workspace_webhooks",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(200), nullable=True),
            sa.Column("url", sa.String(2048), nullable=False),
            sa.Column("secret", sa.String(128), nullable=False),
            sa.Column("events_json", sa.JSON(), nullable=False),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "idx_workspace_webhooks_ws_enabled",
            "workspace_webhooks",
            ["workspace_id", "enabled"],
        )
        op.create_index(
            "ix_workspace_webhooks_workspace_id",
            "workspace_webhooks",
            ["workspace_id"],
        )

    if "webhook_delivery_logs" not in tables:
        op.create_table(
            "webhook_delivery_logs",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "webhook_id",
                sa.String(36),
                sa.ForeignKey("workspace_webhooks.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("workspace_id", sa.String(36), nullable=False),
            sa.Column("event_type", sa.String(64), nullable=False),
            sa.Column("success", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("status_code", sa.Integer(), nullable=True),
            sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("latency_ms", sa.Integer(), nullable=True),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index(
            "idx_webhook_delivery_logs_hook_created",
            "webhook_delivery_logs",
            ["webhook_id", "created_at"],
        )
        op.create_index(
            "ix_webhook_delivery_logs_webhook_id",
            "webhook_delivery_logs",
            ["webhook_id"],
        )
        op.create_index(
            "ix_webhook_delivery_logs_workspace_id",
            "webhook_delivery_logs",
            ["workspace_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "webhook_delivery_logs" in tables:
        op.drop_table("webhook_delivery_logs")
    if "workspace_webhooks" in tables:
        op.drop_table("workspace_webhooks")
