"""sla_policies.calendar JSON nullable (E56)

Revision ID: o1d2e3f4a5b9
Revises: n0c1d2e3f4a8
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "o1d2e3f4a5b9"
down_revision: Union[str, None] = "n0c1d2e3f4a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "sla_policies" not in tables:
        return
    cols = {c["name"] for c in inspector.get_columns("sla_policies")}
    if "calendar" in cols:
        return
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.add_column(
        "sla_policies",
        sa.Column("calendar", json_type, nullable=True),
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "sla_policies" not in tables:
        return
    cols = {c["name"] for c in inspector.get_columns("sla_policies")}
    if "calendar" in cols:
        op.drop_column("sla_policies", "calendar")
