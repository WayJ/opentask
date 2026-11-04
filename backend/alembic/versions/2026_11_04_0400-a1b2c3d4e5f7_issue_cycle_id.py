"""issues.cycle_id + estimate_points（E6-S2）

Revision ID: a1b2c3d4e5f7
Revises: f0e1d2c3b4a5
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f7"
down_revision: Union[str, None] = "f0e1d2c3b4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("issues")}
    indexes = {i["name"] for i in inspector.get_indexes("issues")}

    if "cycle_id" not in cols:
        op.add_column(
            "issues",
            sa.Column(
                "cycle_id",
                sa.String(36),
                sa.ForeignKey("cycles.id", ondelete="SET NULL"),
                nullable=True,
                comment="所属 Cycle ID",
            ),
        )
    if "estimate_points" not in cols:
        op.add_column(
            "issues",
            sa.Column(
                "estimate_points",
                sa.Numeric(8, 2),
                nullable=True,
                comment="故事点估算（可选）",
            ),
        )

    # refresh inspector after adds
    inspector = sa.inspect(bind)
    indexes = {i["name"] for i in inspector.get_indexes("issues")}
    if "idx_issues_cycle" not in indexes:
        op.create_index("idx_issues_cycle", "issues", ["cycle_id"])
    if "ix_issues_cycle_id" not in indexes:
        op.create_index("ix_issues_cycle_id", "issues", ["cycle_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("issues")}
    indexes = {i["name"] for i in inspector.get_indexes("issues")}

    if "ix_issues_cycle_id" in indexes:
        op.drop_index("ix_issues_cycle_id", table_name="issues")
    if "idx_issues_cycle" in indexes:
        op.drop_index("idx_issues_cycle", table_name="issues")
    if "estimate_points" in cols:
        op.drop_column("issues", "estimate_points")
    if "cycle_id" in cols:
        op.drop_column("issues", "cycle_id")
