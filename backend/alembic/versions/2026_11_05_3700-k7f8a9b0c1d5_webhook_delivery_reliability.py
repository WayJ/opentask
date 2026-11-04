"""webhook_delivery_logs reliability columns (E44)

Revision ID: k7f8a9b0c1d5
Revises: j6e7f8a9b0c4
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "k7f8a9b0c1d5"
down_revision: Union[str, None] = "j6e7f8a9b0c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "webhook_delivery_logs" not in tables:
        return
    cols = {c["name"] for c in inspector.get_columns("webhook_delivery_logs")}
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    if "delivery_id" not in cols:
        op.add_column(
            "webhook_delivery_logs",
            sa.Column("delivery_id", sa.String(length=64), nullable=True),
        )
        op.create_index(
            "idx_webhook_delivery_logs_delivery_id",
            "webhook_delivery_logs",
            ["delivery_id"],
        )
    if "payload_json" not in cols:
        op.add_column(
            "webhook_delivery_logs",
            sa.Column("payload_json", json_type, nullable=True),
        )
    if "status" not in cols:
        op.add_column(
            "webhook_delivery_logs",
            sa.Column("status", sa.String(length=32), nullable=True),
        )
    if "next_attempt_at" not in cols:
        op.add_column(
            "webhook_delivery_logs",
            sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
        )
    if "max_attempts" not in cols:
        op.add_column(
            "webhook_delivery_logs",
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="5"),
        )
    # composite for run-due scan
    existing_indexes = {i["name"] for i in inspector.get_indexes("webhook_delivery_logs")}
    if "idx_webhook_delivery_logs_ws_status_next" not in existing_indexes:
        op.create_index(
            "idx_webhook_delivery_logs_ws_status_next",
            "webhook_delivery_logs",
            ["workspace_id", "status", "next_attempt_at"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "webhook_delivery_logs" not in tables:
        return
    existing_indexes = {i["name"] for i in inspector.get_indexes("webhook_delivery_logs")}
    if "idx_webhook_delivery_logs_ws_status_next" in existing_indexes:
        op.drop_index(
            "idx_webhook_delivery_logs_ws_status_next",
            table_name="webhook_delivery_logs",
        )
    if "idx_webhook_delivery_logs_delivery_id" in existing_indexes:
        op.drop_index(
            "idx_webhook_delivery_logs_delivery_id",
            table_name="webhook_delivery_logs",
        )
    cols = {c["name"] for c in inspector.get_columns("webhook_delivery_logs")}
    for name in ("max_attempts", "next_attempt_at", "status", "payload_json", "delivery_id"):
        if name in cols:
            op.drop_column("webhook_delivery_logs", name)
