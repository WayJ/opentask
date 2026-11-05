"""SLA v2 thin: pause_statuses + paused clock columns (E45)

Revision ID: l8a9b0c1d2e6
Revises: k7f8a9b0c1d5
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "l8a9b0c1d2e6"
down_revision: Union[str, None] = "k7f8a9b0c1d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    if "sla_policies" in tables:
        cols = {c["name"] for c in inspector.get_columns("sla_policies")}
        if "pause_statuses" not in cols:
            op.add_column(
                "sla_policies",
                sa.Column(
                    "pause_statuses",
                    json_type,
                    nullable=False,
                    server_default=sa.text("'[]'"),
                ),
            )

    if "issue_sla_clocks" in tables:
        cols = {c["name"] for c in inspector.get_columns("issue_sla_clocks")}
        if "elapsed_before_pause_minutes" not in cols:
            op.add_column(
                "issue_sla_clocks",
                sa.Column(
                    "elapsed_before_pause_minutes",
                    sa.Integer(),
                    nullable=False,
                    server_default="0",
                ),
            )
        if "paused_at" not in cols:
            op.add_column(
                "issue_sla_clocks",
                sa.Column("paused_at", sa.DateTime(), nullable=True),
            )
        if "segment_started_at" not in cols:
            op.add_column(
                "issue_sla_clocks",
                sa.Column("segment_started_at", sa.DateTime(), nullable=True),
            )
        # Backfill segment_started_at for existing running clocks from started_at
        op.execute(
            sa.text(
                "UPDATE issue_sla_clocks "
                "SET segment_started_at = started_at "
                "WHERE status = 'running' AND segment_started_at IS NULL"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_sla_clocks" in tables:
        cols = {c["name"] for c in inspector.get_columns("issue_sla_clocks")}
        for col in ("segment_started_at", "paused_at", "elapsed_before_pause_minutes"):
            if col in cols:
                op.drop_column("issue_sla_clocks", col)
    if "sla_policies" in tables:
        cols = {c["name"] for c in inspector.get_columns("sla_policies")}
        if "pause_statuses" in cols:
            op.drop_column("sla_policies", "pause_statuses")
