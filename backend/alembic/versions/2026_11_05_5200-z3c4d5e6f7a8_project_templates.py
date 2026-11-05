"""project_templates (E72)

Revision ID: z3c4d5e6f7a8
Revises: y2b3c4d5e6f7
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "z3c4d5e6f7a8"
down_revision: Union[str, None] = "y2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "project_templates" in set(inspector.get_table_names()):
        return
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "project_templates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(64), nullable=True),
        sa.Column("payload", json_type, nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source", sa.String(16), nullable=False, server_default="custom"),
        sa.Column("seed_key", sa.String(64), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("workspace_id", "name", name="uq_project_templates_ws_name"),
        sa.UniqueConstraint("workspace_id", "seed_key", name="uq_project_templates_ws_seed"),
    )
    op.create_index("ix_project_templates_workspace_id", "project_templates", ["workspace_id"])
    op.create_index(
        "idx_project_templates_ws_sort",
        "project_templates",
        ["workspace_id", "sort_order"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "project_templates" not in set(inspector.get_table_names()):
        return
    op.drop_index("idx_project_templates_ws_sort", table_name="project_templates")
    op.drop_index("ix_project_templates_workspace_id", table_name="project_templates")
    op.drop_table("project_templates")
