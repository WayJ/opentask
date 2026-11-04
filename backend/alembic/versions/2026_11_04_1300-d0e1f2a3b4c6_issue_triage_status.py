"""issues.triage_status (E9-S1 Triage)

Revision ID: d0e1f2a3b4c6
Revises: c9d0e1f2a3b5
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c6"
down_revision: Union[str, None] = "c9d0e1f2a3b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("issues")}
    if "triage_status" not in cols:
        op.add_column(
            "issues",
            sa.Column("triage_status", sa.String(16), nullable=True, comment="pending|null"),
        )
    indexes = {i["name"] for i in inspector.get_indexes("issues")}
    if "idx_issues_ws_triage" not in indexes:
        op.create_index(
            "idx_issues_ws_triage",
            "issues",
            ["workspace_id", "triage_status"],
        )
    # also single-column index named like model (optional)
    if "ix_issues_triage_status" not in indexes and "idx_issues_triage_status" not in indexes:
        # SQLAlchemy Mapped index=True may expect ix_issues_triage_status
        try:
            op.create_index("ix_issues_triage_status", "issues", ["triage_status"])
        except Exception:
            pass


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {i["name"] for i in inspector.get_indexes("issues")}
    for name in ("idx_issues_ws_triage", "ix_issues_triage_status", "idx_issues_triage_status"):
        if name in indexes:
            op.drop_index(name, table_name="issues")
    cols = {c["name"] for c in inspector.get_columns("issues")}
    if "triage_status" in cols:
        op.drop_column("issues", "triage_status")
