"""initiative_relations (E65)

Revision ID: w9f0a1b2c3d7
Revises: v8e9f0a1b2c6
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "w9f0a1b2c3d7"
down_revision: Union[str, None] = "v8e9f0a1b2c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "initiative_relations" not in tables:
        op.create_table(
            "initiative_relations",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "source_initiative_id",
                sa.String(36),
                sa.ForeignKey("initiatives.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "target_initiative_id",
                sa.String(36),
                sa.ForeignKey("initiatives.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("relation_type", sa.String(32), nullable=False),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint(
                "source_initiative_id",
                "target_initiative_id",
                "relation_type",
                name="uq_initiative_relations_src_tgt_type",
            ),
        )
        op.create_index(
            "idx_initiative_relations_ws_source",
            "initiative_relations",
            ["workspace_id", "source_initiative_id"],
        )
        op.create_index(
            "idx_initiative_relations_ws_target",
            "initiative_relations",
            ["workspace_id", "target_initiative_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "initiative_relations" in tables:
        op.drop_table("initiative_relations")
