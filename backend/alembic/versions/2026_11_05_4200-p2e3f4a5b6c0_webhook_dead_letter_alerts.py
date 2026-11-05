"""webhook dead-letter alerts settings + dedup + pref (E57)

Revision ID: p2e3f4a5b6c0
Revises: o1d2e3f4a5b9
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "p2e3f4a5b6c0"
down_revision: Union[str, None] = "o1d2e3f4a5b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    if "workspaces" in tables:
        cols = {c["name"] for c in inspector.get_columns("workspaces")}
        if "webhook_alert_settings" not in cols:
            op.add_column(
                "workspaces",
                sa.Column("webhook_alert_settings", json_type, nullable=True),
            )

    if "workspace_webhooks" in tables:
        cols = {c["name"] for c in inspector.get_columns("workspace_webhooks")}
        if "alert_settings" not in cols:
            op.add_column(
                "workspace_webhooks",
                sa.Column("alert_settings", json_type, nullable=True),
            )
        if "paused_reason" not in cols:
            op.add_column(
                "workspace_webhooks",
                sa.Column("paused_reason", sa.String(64), nullable=True),
            )

    if "notification_preferences" in tables:
        cols = {c["name"] for c in inspector.get_columns("notification_preferences")}
        if "webhook_delivery_alert" not in cols:
            op.add_column(
                "notification_preferences",
                sa.Column(
                    "webhook_delivery_alert",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("1")
                    if bind.dialect.name == "sqlite"
                    else sa.text("true"),
                ),
            )

    if "webhook_alert_deliveries" not in tables:
        op.create_table(
            "webhook_alert_deliveries",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("webhook_id_key", sa.String(36), nullable=False, server_default=""),
            sa.Column(
                "webhook_id",
                sa.String(36),
                sa.ForeignKey("workspace_webhooks.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column("rule_kind", sa.String(32), nullable=False),
            sa.Column("bucket", sa.String(64), nullable=False),
            sa.Column("notification_id", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint(
                "workspace_id",
                "webhook_id_key",
                "rule_kind",
                "bucket",
                name="uq_webhook_alert_dedupe",
            ),
        )
        op.create_index(
            "idx_webhook_alert_ws_bucket",
            "webhook_alert_deliveries",
            ["workspace_id", "bucket"],
        )
        op.create_index(
            "ix_webhook_alert_deliveries_workspace_id",
            "webhook_alert_deliveries",
            ["workspace_id"],
        )
        op.create_index(
            "ix_webhook_alert_deliveries_webhook_id",
            "webhook_alert_deliveries",
            ["webhook_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "webhook_alert_deliveries" in tables:
        op.drop_table("webhook_alert_deliveries")
    if "notification_preferences" in tables:
        cols = {c["name"] for c in inspector.get_columns("notification_preferences")}
        if "webhook_delivery_alert" in cols:
            op.drop_column("notification_preferences", "webhook_delivery_alert")
    if "workspace_webhooks" in tables:
        cols = {c["name"] for c in inspector.get_columns("workspace_webhooks")}
        if "paused_reason" in cols:
            op.drop_column("workspace_webhooks", "paused_reason")
        if "alert_settings" in cols:
            op.drop_column("workspace_webhooks", "alert_settings")
    if "workspaces" in tables:
        cols = {c["name"] for c in inspector.get_columns("workspaces")}
        if "webhook_alert_settings" in cols:
            op.drop_column("workspaces", "webhook_alert_settings")
