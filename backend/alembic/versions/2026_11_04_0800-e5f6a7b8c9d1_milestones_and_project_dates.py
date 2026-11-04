"""milestones + issues.milestone_id + projects.starts_at/target_date（E8-S1）

Revision ID: e5f6a7b8c9d1
Revises: d4e5f6a7b8c0
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d1"
down_revision: Union[str, None] = "d4e5f6a7b8c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "milestones" not in tables:
        op.create_table(
            "milestones",
            sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("target_date", sa.DateTime(), nullable=True),
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=False,
                server_default="planned",
            ),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(
                ["workspace_id"], ["workspaces.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(
                ["project_id"], ["projects.id"], ondelete="CASCADE"
            ),
        )
        op.create_index("ix_milestones_workspace_id", "milestones", ["workspace_id"])
        op.create_index("ix_milestones_project_id", "milestones", ["project_id"])
        op.create_index(
            "ix_milestones_project_position", "milestones", ["project_id", "position"]
        )

    inspector = sa.inspect(bind)
    project_cols = {c["name"] for c in inspector.get_columns("projects")}
    if "starts_at" not in project_cols:
        op.add_column("projects", sa.Column("starts_at", sa.DateTime(), nullable=True))
    if "target_date" not in project_cols:
        op.add_column("projects", sa.Column("target_date", sa.DateTime(), nullable=True))

    issue_cols = {c["name"] for c in inspector.get_columns("issues")}
    if "milestone_id" not in issue_cols:
        op.add_column(
            "issues",
            sa.Column(
                "milestone_id",
                sa.String(36),
                sa.ForeignKey("milestones.id", ondelete="SET NULL"),
                nullable=True,
                comment="所属里程碑 ID",
            ),
        )
    inspector = sa.inspect(bind)
    indexes = {i["name"] for i in inspector.get_indexes("issues")}
    if "idx_issues_milestone" not in indexes:
        op.create_index("idx_issues_milestone", "issues", ["milestone_id"])
    if "ix_issues_milestone_id" not in indexes:
        op.create_index("ix_issues_milestone_id", "issues", ["milestone_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issues" in tables:
        issue_cols = {c["name"] for c in inspector.get_columns("issues")}
        indexes = {i["name"] for i in inspector.get_indexes("issues")}
        if "ix_issues_milestone_id" in indexes:
            op.drop_index("ix_issues_milestone_id", table_name="issues")
        if "idx_issues_milestone" in indexes:
            op.drop_index("idx_issues_milestone", table_name="issues")
        if "milestone_id" in issue_cols:
            op.drop_column("issues", "milestone_id")

    if "projects" in tables:
        project_cols = {c["name"] for c in inspector.get_columns("projects")}
        if "target_date" in project_cols:
            op.drop_column("projects", "target_date")
        if "starts_at" in project_cols:
            op.drop_column("projects", "starts_at")

    tables = set(sa.inspect(bind).get_table_names())
    if "milestones" in tables:
        op.drop_index("ix_milestones_project_position", table_name="milestones")
        op.drop_index("ix_milestones_project_id", table_name="milestones")
        op.drop_index("ix_milestones_workspace_id", table_name="milestones")
        op.drop_table("milestones")
