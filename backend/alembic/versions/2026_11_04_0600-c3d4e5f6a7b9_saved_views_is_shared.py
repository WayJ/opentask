"""issue_saved_views.is_shared（E7-S2 Shared Saved Views）

Revision ID: c3d4e5f6a7b9
Revises: b2c3d4e5f6a8
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b9"
down_revision: Union[str, None] = "b2c3d4e5f6a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_saved_views" not in tables:
        return

    cols = {c["name"] for c in inspector.get_columns("issue_saved_views")}
    if "is_shared" not in cols:
        op.add_column(
            "issue_saved_views",
            sa.Column(
                "is_shared",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    indexes = {i["name"] for i in inspector.get_indexes("issue_saved_views")}
    if "idx_saved_views_ws_shared" not in indexes:
        op.create_index(
            "idx_saved_views_ws_shared",
            "issue_saved_views",
            ["workspace_id", "is_shared"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_saved_views" not in tables:
        return

    indexes = {i["name"] for i in inspector.get_indexes("issue_saved_views")}
    if "idx_saved_views_ws_shared" in indexes:
        op.drop_index("idx_saved_views_ws_shared", table_name="issue_saved_views")

    cols = {c["name"] for c in inspector.get_columns("issue_saved_views")}
    if "is_shared" in cols:
        op.drop_column("issue_saved_views", "is_shared")
