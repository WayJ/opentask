"""Workspace 租户表 + Project/Issue.workspace_id 回填

Revision ID: a1b2c3d4e5f6
Revises: b7e2c9140d3a
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "b7e2c9140d3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_WS_ID = "00000000-0000-4000-8000-000000000001"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "workspaces" not in tables:
        op.create_table(
            "workspaces",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("slug", sa.String(80), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_by", sa.String(36), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("slug", name="uq_workspaces_slug"),
        )
        op.create_index("idx_workspaces_created_by", "workspaces", ["created_by"])

    if "workspace_members" not in tables:
        op.create_table(
            "workspace_members",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", sa.String(36), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_ws_user"),
        )
        op.create_index("idx_workspace_members_user", "workspace_members", ["user_id"])
        op.create_index("ix_workspace_members_workspace_id", "workspace_members", ["workspace_id"])

    # projects.workspace_id
    proj_cols = {c["name"] for c in inspector.get_columns("projects")} if "projects" in tables else set()
    if "projects" in tables and "workspace_id" not in proj_cols:
        op.add_column("projects", sa.Column("workspace_id", sa.String(36), nullable=True))
        op.create_index("idx_projects_workspace", "projects", ["workspace_id"])
        op.create_foreign_key(
            "fk_projects_workspace_id_workspaces",
            "projects",
            "workspaces",
            ["workspace_id"],
            ["id"],
        )

    # issues.workspace_id
    issue_cols = {c["name"] for c in inspector.get_columns("issues")} if "issues" in tables else set()
    if "issues" in tables and "workspace_id" not in issue_cols:
        op.add_column("issues", sa.Column("workspace_id", sa.String(36), nullable=True))
        op.create_index("idx_issues_workspace", "issues", ["workspace_id"])
        op.create_foreign_key(
            "fk_issues_workspace_id_workspaces",
            "issues",
            "workspaces",
            ["workspace_id"],
            ["id"],
        )

    # 插入默认工作区 + 回填
    op.execute(
        sa.text(
            """
            INSERT INTO workspaces (id, name, slug, description, created_by, created_at, updated_at)
            SELECT :id, 'Default Workspace', 'default', 'System default workspace for legacy rows', NULL, NOW(), NOW()
            WHERE NOT EXISTS (SELECT 1 FROM workspaces WHERE slug = 'default')
            """
        ).bindparams(id=DEFAULT_WS_ID)
    )

    # 取实际 default id（可能已存在）
    default_id = bind.execute(sa.text("SELECT id FROM workspaces WHERE slug = 'default' LIMIT 1")).scalar()
    if default_id:
        if "projects" in tables:
            op.execute(
                sa.text("UPDATE projects SET workspace_id = :wid WHERE workspace_id IS NULL").bindparams(
                    wid=default_id
                )
            )
        if "issues" in tables:
            op.execute(
                sa.text("UPDATE issues SET workspace_id = :wid WHERE workspace_id IS NULL").bindparams(
                    wid=default_id
                )
            )
        # 存量用户加入默认工作区（member）
        if "user" in tables:
            users = bind.execute(sa.text("SELECT id FROM \"user\"")).fetchall()
            for (uid,) in users:
                exists = bind.execute(
                    sa.text(
                        "SELECT 1 FROM workspace_members WHERE workspace_id = :w AND user_id = :u LIMIT 1"
                    ),
                    {"w": default_id, "u": str(uid)},
                ).first()
                if not exists:
                    bind.execute(
                        sa.text(
                            "INSERT INTO workspace_members (id, workspace_id, user_id, role, created_at) "
                            "VALUES (:id, :w, :u, 'member', NOW())"
                        ),
                        {"id": str(uuid.uuid4()), "w": default_id, "u": str(uid)},
                    )

    # 调整 projects 名称唯一：去掉全局 unique，改为 (workspace_id, name)
    if "projects" in tables:
        # 尝试 drop 旧唯一约束/索引（名称因方言而异，探测后删除）
        for uq in inspector.get_unique_constraints("projects"):
            cols = uq.get("column_names") or []
            if cols == ["name"] or set(cols) == {"name"}:
                op.drop_constraint(uq["name"], "projects", type_="unique")
        for ix in inspector.get_indexes("projects"):
            if ix.get("unique") and (ix.get("column_names") == ["name"]):
                op.drop_index(ix["name"], table_name="projects")
        # 复合唯一索引（若不存在）
        ix_names = {ix["name"] for ix in inspector.get_indexes("projects")}
        uq_names = {uq["name"] for uq in inspector.get_unique_constraints("projects")}
        if "uq_projects_workspace_name" not in ix_names and "uq_projects_workspace_name" not in uq_names:
            op.create_index(
                "uq_projects_workspace_name",
                "projects",
                ["workspace_id", "name"],
                unique=True,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "projects" in tables:
        cols = {c["name"] for c in inspector.get_columns("projects")}
        if "workspace_id" in cols:
            op.drop_constraint("fk_projects_workspace_id_workspaces", "projects", type_="foreignkey")
            op.drop_index("idx_projects_workspace", table_name="projects")
            try:
                op.drop_index("uq_projects_workspace_name", table_name="projects")
            except Exception:
                pass
            op.drop_column("projects", "workspace_id")

    if "issues" in tables:
        cols = {c["name"] for c in inspector.get_columns("issues")}
        if "workspace_id" in cols:
            op.drop_constraint("fk_issues_workspace_id_workspaces", "issues", type_="foreignkey")
            op.drop_index("idx_issues_workspace", table_name="issues")
            op.drop_column("issues", "workspace_id")

    if "workspace_members" in tables:
        op.drop_table("workspace_members")
    if "workspaces" in tables:
        op.drop_table("workspaces")
