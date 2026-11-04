"""project health updates + watchers + project health cache (E8-S2)

Revision ID: f6a7b8c9d0e2
Revises: e5f6a7b8c9d1
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e2"
down_revision: Union[str, None] = "e5f6a7b8c9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    project_cols = {c["name"] for c in inspector.get_columns("projects")}
    if "health_status" not in project_cols:
        op.add_column("projects", sa.Column("health_status", sa.String(20), nullable=True))
    if "health_note" not in project_cols:
        op.add_column("projects", sa.Column("health_note", sa.Text(), nullable=True))
    if "health_updated_at" not in project_cols:
        op.add_column("projects", sa.Column("health_updated_at", sa.DateTime(), nullable=True))
    if "health_updated_by" not in project_cols:
        op.add_column("projects", sa.Column("health_updated_by", sa.String(36), nullable=True))

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "project_health_updates" not in tables:
        op.create_table(
            "project_health_updates",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("workspace_id", sa.String(36), nullable=False),
            sa.Column("project_id", sa.String(36), nullable=False),
            sa.Column("status", sa.String(20), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("actor_user_id", sa.String(36), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        )
        op.create_index("ix_project_health_updates_workspace_id", "project_health_updates", ["workspace_id"])
        op.create_index("ix_project_health_updates_project_id", "project_health_updates", ["project_id"])
        op.create_index("ix_phu_project_created", "project_health_updates", ["project_id", "created_at"])

    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "project_watchers" not in tables:
        op.create_table(
            "project_watchers",
            sa.Column("id", sa.String(36), primary_key=True, nullable=False),
            sa.Column("workspace_id", sa.String(36), nullable=False),
            sa.Column("project_id", sa.String(36), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("project_id", "user_id", name="uq_project_watchers_project_user"),
        )
        op.create_index("ix_project_watchers_workspace_id", "project_watchers", ["workspace_id"])
        op.create_index("ix_project_watchers_project_id", "project_watchers", ["project_id"])
        op.create_index("ix_project_watchers_user_id", "project_watchers", ["user_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "project_watchers" in tables:
        op.drop_table("project_watchers")
    if "project_health_updates" in tables:
        op.drop_table("project_health_updates")
    project_cols = {c["name"] for c in inspector.get_columns("projects")}
    for col in ("health_updated_by", "health_updated_at", "health_note", "health_status"):
        if col in project_cols:
            op.drop_column("projects", col)
