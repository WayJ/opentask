"""issue_formula_cache query cache (E43) — non-emit

Revision ID: j6e7f8a9b0c4
Revises: i5d6e7f8a9b3
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "j6e7f8a9b0c4"
down_revision: Union[str, None] = "i5d6e7f8a9b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_formula_cache" in tables:
        return

    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "issue_formula_cache",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(length=36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "issue_id",
            sa.String(length=36),
            sa.ForeignKey("issues.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "field_id",
            sa.String(length=36),
            sa.ForeignKey("custom_fields.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("value_json", json_type, nullable=True),
        sa.Column("error", sa.String(length=64), nullable=True),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("issue_id", "field_id", name="uq_issue_formula_cache_issue_field"),
    )
    op.create_index(
        "idx_issue_formula_cache_ws_field",
        "issue_formula_cache",
        ["workspace_id", "field_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_formula_cache" not in tables:
        return
    op.drop_index("idx_issue_formula_cache_ws_field", table_name="issue_formula_cache")
    op.drop_table("issue_formula_cache")
