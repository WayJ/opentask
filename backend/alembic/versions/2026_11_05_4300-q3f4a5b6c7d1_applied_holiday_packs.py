"""applied holiday packs ledger on WS + policy (E58)

Revision ID: q3f4a5b6c7d1
Revises: p2e3f4a5b6c0
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "q3f4a5b6c7d1"
down_revision: Union[str, None] = "p2e3f4a5b6c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")

    if "workspaces" in tables:
        cols = {c["name"] for c in inspector.get_columns("workspaces")}
        if "applied_holiday_packs" not in cols:
            op.add_column(
                "workspaces",
                sa.Column("applied_holiday_packs", json_type, nullable=True),
            )

    if "sla_policies" in tables:
        cols = {c["name"] for c in inspector.get_columns("sla_policies")}
        if "applied_holiday_packs" not in cols:
            op.add_column(
                "sla_policies",
                sa.Column("applied_holiday_packs", json_type, nullable=True),
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "sla_policies" in tables:
        cols = {c["name"] for c in inspector.get_columns("sla_policies")}
        if "applied_holiday_packs" in cols:
            op.drop_column("sla_policies", "applied_holiday_packs")
    if "workspaces" in tables:
        cols = {c["name"] for c in inspector.get_columns("workspaces")}
        if "applied_holiday_packs" in cols:
            op.drop_column("workspaces", "applied_holiday_packs")
