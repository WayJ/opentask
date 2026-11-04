"""issues.parent_issue_id（E4-S3 一等公民子 Issue）

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("issues")}
    if "parent_issue_id" not in cols:
        op.add_column(
            "issues",
            sa.Column(
                "parent_issue_id",
                sa.String(36),
                sa.ForeignKey("issues.id", ondelete="SET NULL"),
                nullable=True,
                comment="父 Issue ID",
            ),
        )
        op.create_index("idx_issues_parent", "issues", ["parent_issue_id"])
        op.create_index("ix_issues_parent_issue_id", "issues", ["parent_issue_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("issues")}
    if "parent_issue_id" in cols:
        indexes = {i["name"] for i in inspector.get_indexes("issues")}
        if "ix_issues_parent_issue_id" in indexes:
            op.drop_index("ix_issues_parent_issue_id", table_name="issues")
        if "idx_issues_parent" in indexes:
            op.drop_index("idx_issues_parent", table_name="issues")
        op.drop_column("issues", "parent_issue_id")
