"""initiatives + initiative_projects (E10-S1)

Revision ID: b2c3d4e5f6a7
Revises: f2a3b4c5d6e8
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "f2a3b4c5d6e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "initiatives" not in tables:
        op.create_table(
            "initiatives",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="active"),
            sa.Column("target_date", sa.DateTime(), nullable=True),
            sa.Column("owner_user_id", sa.String(36), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("workspace_id", "name", name="uq_initiatives_ws_name"),
        )
        op.create_index("idx_initiatives_ws_sort", "initiatives", ["workspace_id", "sort_order"])
        op.create_index("idx_initiatives_ws_status", "initiatives", ["workspace_id", "status"])
        op.create_index("ix_initiatives_workspace_id", "initiatives", ["workspace_id"])

    tables = set(sa.inspect(bind).get_table_names())
    if "initiative_projects" not in tables:
        op.create_table(
            "initiative_projects",
            sa.Column("initiative_id", sa.String(36), sa.ForeignKey("initiatives.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("idx_initiative_projects_project", "initiative_projects", ["project_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "initiative_projects" in tables:
        op.drop_table("initiative_projects")
    if "initiatives" in tables:
        op.drop_table("initiatives")
