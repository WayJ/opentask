"""insights saved reports visibility personal|workspace (E61)

Revision ID: t6c7d8e9f0a4
Revises: s5b6c7d8e9f3
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "t6c7d8e9f0a4"
down_revision: Union[str, None] = "s5b6c7d8e9f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "insights_saved_reports" not in tables:
        return
    cols = {c["name"] for c in inspector.get_columns("insights_saved_reports")}
    if "visibility" not in cols:
        op.add_column(
            "insights_saved_reports",
            sa.Column(
                "visibility",
                sa.String(16),
                nullable=False,
                server_default="personal",
            ),
        )
        op.execute(
            sa.text(
                "UPDATE insights_saved_reports SET visibility = 'personal' "
                "WHERE visibility IS NULL OR visibility = ''"
            )
        )
    indexes = {i["name"] for i in inspector.get_indexes("insights_saved_reports")}
    if "idx_insights_reports_ws_visibility" not in indexes:
        op.create_index(
            "idx_insights_reports_ws_visibility",
            "insights_saved_reports",
            ["workspace_id", "visibility"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "insights_saved_reports" not in inspector.get_table_names():
        return
    indexes = {i["name"] for i in inspector.get_indexes("insights_saved_reports")}
    if "idx_insights_reports_ws_visibility" in indexes:
        op.drop_index(
            "idx_insights_reports_ws_visibility",
            table_name="insights_saved_reports",
        )
    cols = {c["name"] for c in inspector.get_columns("insights_saved_reports")}
    if "visibility" in cols:
        op.drop_column("insights_saved_reports", "visibility")
