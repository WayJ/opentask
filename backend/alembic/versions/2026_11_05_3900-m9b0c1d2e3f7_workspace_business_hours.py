"""workspace timezone + business_hours (E50)

Revision ID: m9b0c1d2e3f7
Revises: l8a9b0c1d2e6
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "m9b0c1d2e3f7"
down_revision: Union[str, None] = "l8a9b0c1d2e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    if "workspaces" not in tables:
        return
    cols = {c["name"] for c in inspector.get_columns("workspaces")}
    if "timezone" not in cols:
        op.add_column(
            "workspaces",
            sa.Column("timezone", sa.String(64), nullable=True),
        )
    if "business_hours" not in cols:
        op.add_column(
            "workspaces",
            sa.Column(
                "business_hours",
                json_type,
                nullable=True,
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "workspaces" not in tables:
        return
    cols = {c["name"] for c in inspector.get_columns("workspaces")}
    if "business_hours" in cols:
        op.drop_column("workspaces", "business_hours")
    if "timezone" in cols:
        op.drop_column("workspaces", "timezone")
