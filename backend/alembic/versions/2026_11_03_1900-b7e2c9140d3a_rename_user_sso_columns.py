"""user 表的 SSO 相关列改名

背景：仓内去掉了上游用户中心（SSO）的品牌字样，`user` 表上对应的四列与唯一约束
一并改名：

    jnpf_user_id  → sso_user_id
    jnpf_token    → sso_token
    jnpf_account  → sso_account
    jnpf_name     → sso_name
    uq_user_jnpf_user_id → uq_user_sso_user_id

基线迁移（``003ccd38d5cd``）已同步改成新列名，因此**全新库**直接建出来就是新列，
本迁移对它是空操作；而**存量库**（本地开发库、已部署环境）上仍是旧列名，由本迁移
完成改名。故这里用 inspector 先探测再动手——两种库都能安全跑。

Revision ID: b7e2c9140d3a
Revises: c4f8a2b91d6e
"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e2c9140d3a"
down_revision: Union[str, None] = "c4f8a2b91d6e"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None

# 旧列名 → 新列名
_COLUMN_RENAMES = {
    "jnpf_user_id": "sso_user_id",
    "jnpf_token": "sso_token",
    "jnpf_account": "sso_account",
    "jnpf_name": "sso_name",
}

# 旧唯一约束名 → 新唯一约束名
_CONSTRAINT_RENAMES = {
    "uq_user_jnpf_user_id": "uq_user_sso_user_id",
}


def _existing_columns() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {col["name"] for col in inspector.get_columns("user")}


def _existing_constraints() -> set[str]:
    inspector = sa.inspect(op.get_bind())
    names: set[str] = set()
    for uc in inspector.get_unique_constraints("user"):
        if uc.get("name"):
            names.add(uc["name"])
    for idx in inspector.get_indexes("user"):
        if idx.get("name"):
            names.add(idx["name"])
    return names


def upgrade() -> None:
    columns = _existing_columns()
    for old, new in _COLUMN_RENAMES.items():
        if old in columns and new not in columns:
            op.alter_column("user", old, new_column_name=new)

    # 唯一约束/索引跟着改名（PostgreSQL 里改列名不会自动改约束名）
    constraints = _existing_constraints()
    for old, new in _CONSTRAINT_RENAMES.items():
        if old in constraints and new not in constraints:
            op.execute(sa.text(f'ALTER TABLE "user" RENAME CONSTRAINT "{old}" TO "{new}"'))


def downgrade() -> None:
    constraints = _existing_constraints()
    for old, new in reversed(list(_CONSTRAINT_RENAMES.items())):
        if new in constraints and old not in constraints:
            op.execute(sa.text(f'ALTER TABLE "user" RENAME CONSTRAINT "{new}" TO "{old}"'))

    columns = _existing_columns()
    for old, new in reversed(list(_COLUMN_RENAMES.items())):
        if new in columns and old not in columns:
            op.alter_column("user", new, new_column_name=old)
