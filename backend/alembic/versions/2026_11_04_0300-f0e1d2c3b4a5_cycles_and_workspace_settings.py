"""cycles 表 + workspaces Cycles 设置列（E6-S1）

Revision ID: f0e1d2c3b4a5
Revises: e1f2a3b4c5d6
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f0e1d2c3b4a5"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "cycles" not in tables:
        op.create_table(
            "cycles",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("number", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="upcoming"),
            sa.Column("starts_at", sa.DateTime(), nullable=False),
            sa.Column("ends_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_cycles_workspace_id", "cycles", ["workspace_id"])
        op.create_index("idx_cycles_ws_status", "cycles", ["workspace_id", "status"])
        op.create_index("idx_cycles_ws_starts", "cycles", ["workspace_id", "starts_at"])

    ws_cols = {c["name"] for c in inspector.get_columns("workspaces")}
    if "cycles_enabled" not in ws_cols:
        op.add_column(
            "workspaces",
            sa.Column(
                "cycles_enabled",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    if "cycle_duration_days" not in ws_cols:
        op.add_column(
            "workspaces",
            sa.Column(
                "cycle_duration_days",
                sa.Integer(),
                nullable=False,
                server_default="14",
            ),
        )
    if "cycle_rollover_policy" not in ws_cols:
        op.add_column(
            "workspaces",
            sa.Column(
                "cycle_rollover_policy",
                sa.String(32),
                nullable=False,
                server_default="into_next",
            ),
        )
    if "cycle_capacity_lookback" not in ws_cols:
        op.add_column(
            "workspaces",
            sa.Column(
                "cycle_capacity_lookback",
                sa.Integer(),
                nullable=False,
                server_default="3",
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    ws_cols = {c["name"] for c in inspector.get_columns("workspaces")} if "workspaces" in tables else set()

    for col in (
        "cycle_capacity_lookback",
        "cycle_rollover_policy",
        "cycle_duration_days",
        "cycles_enabled",
    ):
        if col in ws_cols:
            op.drop_column("workspaces", col)

    if "cycles" in tables:
        indexes = {i["name"] for i in inspector.get_indexes("cycles")}
        for name in ("idx_cycles_ws_starts", "idx_cycles_ws_status", "ix_cycles_workspace_id"):
            if name in indexes:
                op.drop_index(name, table_name="cycles")
        op.drop_table("cycles")
