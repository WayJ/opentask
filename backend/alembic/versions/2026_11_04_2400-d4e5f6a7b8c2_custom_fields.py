"""custom_fields + issue_custom_field_values (E25)

Revision ID: d4e5f6a7b8c2
Revises: c3d4e5f6a7b1
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c2"
down_revision: Union[str, None] = "c3d4e5f6a7b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "custom_fields" not in tables:
        op.create_table(
            "custom_fields",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("key", sa.String(64), nullable=False),
            sa.Column("type", sa.String(32), nullable=False),
            sa.Column("options_json", sa.JSON(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("archived_at", sa.DateTime(), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("workspace_id", "key", name="uq_custom_fields_ws_key"),
        )
        op.create_index(
            "idx_custom_fields_ws_position",
            "custom_fields",
            ["workspace_id", "position"],
        )
        op.create_index("ix_custom_fields_workspace_id", "custom_fields", ["workspace_id"])

    tables = set(sa.inspect(bind).get_table_names())
    if "issue_custom_field_values" not in tables:
        op.create_table(
            "issue_custom_field_values",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "issue_id",
                sa.String(36),
                sa.ForeignKey("issues.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "field_id",
                sa.String(36),
                sa.ForeignKey("custom_fields.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("value_json", sa.JSON(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint(
                "issue_id", "field_id", name="uq_issue_cf_values_issue_field"
            ),
        )
        op.create_index(
            "idx_issue_cf_values_field",
            "issue_custom_field_values",
            ["field_id"],
        )
        op.create_index(
            "ix_issue_custom_field_values_issue_id",
            "issue_custom_field_values",
            ["issue_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "issue_custom_field_values" in tables:
        op.drop_table("issue_custom_field_values")
    if "custom_fields" in tables:
        op.drop_table("custom_fields")
