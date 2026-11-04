"""tag_groups + tags workspace/color/group（E7-S1）

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a8"
down_revision: Union[str, None] = "a1b2c3d4e5f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "tag_groups" not in tables:
        op.create_table(
            "tag_groups",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column(
                "workspace_id",
                sa.String(36),
                sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("color", sa.String(20), nullable=True),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("workspace_id", "name", name="uq_tag_groups_ws_name"),
        )
        op.create_index("ix_tag_groups_workspace_id", "tag_groups", ["workspace_id"])

    inspector = sa.inspect(bind)
    tag_cols = {c["name"] for c in inspector.get_columns("tags")}
    tag_uniques = {u["name"] for u in inspector.get_unique_constraints("tags")}
    tag_indexes = {i["name"] for i in inspector.get_indexes("tags")}

    if "workspace_id" not in tag_cols:
        op.add_column("tags", sa.Column("workspace_id", sa.String(36), nullable=True))
    if "color" not in tag_cols:
        op.add_column(
            "tags",
            sa.Column("color", sa.String(20), nullable=False, server_default="#3b82f6"),
        )
    if "group_id" not in tag_cols:
        op.add_column("tags", sa.Column("group_id", sa.String(36), nullable=True))
    if "updated_at" not in tag_cols:
        op.add_column(
            "tags",
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    # Backfill workspace_id (Q5)
    op.execute(
        sa.text(
            """
            WITH tag_ws AS (
              SELECT
                t.id AS tag_id,
                (
                  SELECT i.workspace_id
                  FROM issue_tags it
                  JOIN issues i ON i.id = it.issue_id
                  WHERE it.tag_id = t.id AND i.workspace_id IS NOT NULL
                  ORDER BY i.created_at ASC NULLS LAST, i.id ASC
                  LIMIT 1
                ) AS ws_from_issue,
                (SELECT w.id FROM workspaces w ORDER BY w.created_at ASC NULLS LAST, w.id ASC LIMIT 1) AS ws_fallback
              FROM tags t
              WHERE t.workspace_id IS NULL
            )
            UPDATE tags AS t
            SET workspace_id = COALESCE(tag_ws.ws_from_issue, tag_ws.ws_fallback)
            FROM tag_ws
            WHERE t.id = tag_ws.tag_id
              AND t.workspace_id IS NULL
              AND COALESCE(tag_ws.ws_from_issue, tag_ws.ws_fallback) IS NOT NULL
            """
        )
    )

    # Resolve duplicate (workspace_id, name) by suffixing later rows
    op.execute(
        sa.text(
            """
            WITH ranked AS (
              SELECT
                id,
                workspace_id,
                name,
                ROW_NUMBER() OVER (PARTITION BY workspace_id, name ORDER BY id) AS rn
              FROM tags
              WHERE workspace_id IS NOT NULL
            )
            UPDATE tags AS t
            SET name = t.name || '-migrated' || CASE WHEN ranked.rn = 2 THEN '' ELSE (ranked.rn - 1)::text END
            FROM ranked
            WHERE t.id = ranked.id AND ranked.rn > 1
            """
        )
    )

    # Drop remaining nulls if any orphan without workspaces — delete impossible; skip
    # Make NOT NULL
    inspector = sa.inspect(bind)
    # If somehow still null and no workspaces, leave nullable briefly — but require NOT NULL for product
    null_left = bind.execute(sa.text("SELECT COUNT(*) FROM tags WHERE workspace_id IS NULL")).scalar()
    if null_left and null_left > 0:
        # create a synthetic default workspace is out of scope; delete orphans only if zero workspaces
        ws_count = bind.execute(sa.text("SELECT COUNT(*) FROM workspaces")).scalar() or 0
        if ws_count == 0:
            op.execute(sa.text("DELETE FROM issue_tags WHERE tag_id IN (SELECT id FROM tags WHERE workspace_id IS NULL)"))
            op.execute(sa.text("DELETE FROM tags WHERE workspace_id IS NULL"))
        else:
            raise RuntimeError(f"tags backfill left {null_left} rows without workspace_id")

    op.alter_column("tags", "workspace_id", existing_type=sa.String(36), nullable=False)

    # FKs + indexes
    inspector = sa.inspect(bind)
    fks = {fk["name"] for fk in inspector.get_foreign_keys("tags")}
    if "fk_tags_workspace_id_workspaces" not in fks:
        op.create_foreign_key(
            "fk_tags_workspace_id_workspaces",
            "tags",
            "workspaces",
            ["workspace_id"],
            ["id"],
            ondelete="CASCADE",
        )
    if "fk_tags_group_id_tag_groups" not in fks:
        op.create_foreign_key(
            "fk_tags_group_id_tag_groups",
            "tags",
            "tag_groups",
            ["group_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if "uq_tags_name" in tag_uniques:
        op.drop_constraint("uq_tags_name", "tags", type_="unique")

    inspector = sa.inspect(bind)
    tag_uniques = {u["name"] for u in inspector.get_unique_constraints("tags")}
    tag_indexes = {i["name"] for i in inspector.get_indexes("tags")}
    if "uq_tags_ws_name" not in tag_uniques:
        op.create_unique_constraint("uq_tags_ws_name", "tags", ["workspace_id", "name"])
    if "ix_tags_workspace_id" not in tag_indexes:
        op.create_index("ix_tags_workspace_id", "tags", ["workspace_id"])
    if "ix_tags_group_id" not in tag_indexes:
        op.create_index("ix_tags_group_id", "tags", ["group_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tag_cols = {c["name"] for c in inspector.get_columns("tags")} if "tags" in inspector.get_table_names() else set()
    tag_uniques = {u["name"] for u in inspector.get_unique_constraints("tags")} if tag_cols else set()
    tag_indexes = {i["name"] for i in inspector.get_indexes("tags")} if tag_cols else set()
    fks = {fk["name"] for fk in inspector.get_foreign_keys("tags")} if tag_cols else set()

    if "uq_tags_ws_name" in tag_uniques:
        op.drop_constraint("uq_tags_ws_name", "tags", type_="unique")
    if "ix_tags_group_id" in tag_indexes:
        op.drop_index("ix_tags_group_id", table_name="tags")
    if "ix_tags_workspace_id" in tag_indexes:
        op.drop_index("ix_tags_workspace_id", table_name="tags")
    if "fk_tags_group_id_tag_groups" in fks:
        op.drop_constraint("fk_tags_group_id_tag_groups", "tags", type_="foreignkey")
    if "fk_tags_workspace_id_workspaces" in fks:
        op.drop_constraint("fk_tags_workspace_id_workspaces", "tags", type_="foreignkey")

    for col in ("updated_at", "group_id", "color", "workspace_id"):
        if col in tag_cols:
            op.drop_column("tags", col)

    # restore global unique (best-effort; may fail if duplicate names)
    inspector = sa.inspect(bind)
    tag_uniques = {u["name"] for u in inspector.get_unique_constraints("tags")}
    if "uq_tags_name" not in tag_uniques:
        op.create_unique_constraint("uq_tags_name", "tags", ["name"])

    tables = set(inspector.get_table_names())
    if "tag_groups" in tables:
        op.drop_index("ix_tag_groups_workspace_id", table_name="tag_groups")
        op.drop_table("tag_groups")
