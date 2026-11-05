"""project lead_id + project_members (E79 roster-only)

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, None] = "d7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "projects" in tables:
        cols = {c["name"] for c in inspector.get_columns("projects")}
        if "lead_id" not in cols:
            op.add_column(
                "projects",
                sa.Column("lead_id", sa.String(36), nullable=True),
            )
            op.create_index("ix_projects_lead_id", "projects", ["lead_id"])

    if "project_members" not in tables:
        op.create_table(
            "project_members",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("workspace_id", sa.String(36), nullable=False),
            sa.Column("project_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("role", sa.String(32), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
        )
        op.create_index("ix_project_members_workspace_id", "project_members", ["workspace_id"])
        op.create_index("ix_project_members_project_id", "project_members", ["project_id"])
        op.create_index("ix_project_members_user_id", "project_members", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "project_members" in tables:
        op.drop_table("project_members")
    if "projects" in tables:
        cols = {c["name"] for c in inspector.get_columns("projects")}
        if "lead_id" in cols:
            op.drop_index("ix_projects_lead_id", table_name="projects")
            op.drop_column("projects", "lead_id")
