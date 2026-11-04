"""formula_expr + formula_result_type on custom_fields (E40)

Revision ID: g3b4c5d6e7f1
Revises: f2a3b4c5d6e0
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g3b4c5d6e7f1"
down_revision: Union[str, None] = "f2a3b4c5d6e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "custom_fields" not in tables:
        return
    cols = {c["name"] for c in inspector.get_columns("custom_fields")}
    if "formula_expr" not in cols:
        op.add_column(
            "custom_fields",
            sa.Column("formula_expr", sa.Text(), nullable=True),
        )
    if "formula_result_type" not in cols:
        op.add_column(
            "custom_fields",
            sa.Column("formula_result_type", sa.String(length=32), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "custom_fields" not in tables:
        return
    cols = {c["name"] for c in inspector.get_columns("custom_fields")}
    if "formula_result_type" in cols:
        op.drop_column("custom_fields", "formula_result_type")
    if "formula_expr" in cols:
        op.drop_column("custom_fields", "formula_expr")
