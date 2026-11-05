"""issue_forms.enqueue_triage (E68)

Revision ID: x1a2b3c4d5e6
Revises: w9f0a1b2c3d7
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "x1a2b3c4d5e6"
down_revision: Union[str, None] = "w9f0a1b2c3d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    cols = (
        {c["name"] for c in inspector.get_columns("issue_forms")}
        if "issue_forms" in tables
        else set()
    )
    if "enqueue_triage" not in cols:
        op.add_column(
            "issue_forms",
            sa.Column(
                "enqueue_triage",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    cols = (
        {c["name"] for c in inspector.get_columns("issue_forms")}
        if "issue_forms" in tables
        else set()
    )
    if "enqueue_triage" in cols:
        op.drop_column("issue_forms", "enqueue_triage")
