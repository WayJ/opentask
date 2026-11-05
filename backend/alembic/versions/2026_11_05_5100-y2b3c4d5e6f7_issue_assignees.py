"""issue_assignees for multi-assignee mid (E71)

Revision ID: y2b3c4d5e6f7
Revises: x1a2b3c4d5e6
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "y2b3c4d5e6f7"
down_revision: Union[str, None] = "x1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_assignees" not in tables:
        op.create_table(
            "issue_assignees",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("workspace_id", sa.String(36), nullable=False),
            sa.Column("issue_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["issue_id"], ["issues.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("issue_id", "user_id", name="uq_issue_assignees_issue_user"),
        )
        op.create_index("ix_issue_assignees_workspace_id", "issue_assignees", ["workspace_id"])
        op.create_index("ix_issue_assignees_issue_id", "issue_assignees", ["issue_id"])
        op.create_index("ix_issue_assignees_user_id", "issue_assignees", ["user_id"])
        op.create_index(
            "ix_issue_assignees_ws_user", "issue_assignees", ["workspace_id", "user_id"]
        )

    # Backfill: existing non-null assignee_id → position=0 junction row
    if "issues" in tables:
        rows = bind.execute(
            sa.text(
                """
                SELECT i.id, i.workspace_id, i.assignee_id
                FROM issues i
                WHERE i.assignee_id IS NOT NULL
                  AND i.workspace_id IS NOT NULL
                  AND NOT EXISTS (
                    SELECT 1 FROM issue_assignees a
                    WHERE a.issue_id = i.id AND a.user_id = i.assignee_id
                  )
                """
            )
        ).fetchall()
        for issue_id, workspace_id, assignee_id in rows:
            bind.execute(
                sa.text(
                    """
                    INSERT INTO issue_assignees
                        (id, workspace_id, issue_id, user_id, position, created_at)
                    VALUES (:id, :wid, :iid, :uid, 0, NOW())
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "wid": str(workspace_id),
                    "iid": str(issue_id),
                    "uid": str(assignee_id),
                },
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issue_assignees" in tables:
        op.drop_table("issue_assignees")
