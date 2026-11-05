"""issues.start_date + timeline_action start_date_changed (E73)

Revision ID: a4b5c6d7e8f9
Revises: z3c4d5e6f7a8
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a4b5c6d7e8f9"
down_revision: Union[str, None] = "z3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("issues")}
    if "start_date" not in cols:
        op.add_column("issues", sa.Column("start_date", sa.DateTime(), nullable=True))
        op.create_index("idx_issues_start_date", "issues", ["start_date"])

    if bind.dialect.name == "postgresql":
        op.execute(
            "ALTER TYPE timeline_action ADD VALUE IF NOT EXISTS 'start_date_changed'"
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("issues")}
    if "start_date" in cols:
        op.drop_index("idx_issues_start_date", table_name="issues")
        op.drop_column("issues", "start_date")
    # PG cannot easily drop enum values; leave as no-op.
