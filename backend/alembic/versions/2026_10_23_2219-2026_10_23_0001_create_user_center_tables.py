"""create user center tables and switch user password column

用户中心建表 + user 表密码列切换 + 业务表 dept_id

内容：
1. 建用户中心 9 张表（department/position/user_dept/role/permission/
   role_permission/user_role/role_dept/refresh_token），字段与
   opentask/models/user_center/model.py 严格一致
2. user 表新增本地账号安全字段（username/password_hash/must_change_password/
   token_version/dingtalk_user_id/failed_attempts/locked_until），
   在线模式回填 username（优先 jnpf_account，其次 name，重名加 _<n> 序号）
   和 password_hash（bcrypt，hash 失败则置 must_change_password=1），
   随后 drop 旧列 password / jwt_token_fingerprint
3. 7 张业务表（requirements/projects/issues/knowledge_bases/documents/
   tasks/agent_tasks）新增 dept_id 列 + ix_<table>_dept_id 索引

downgrade 注意：password_hash 不可逆，回滚后重建的 password 列全部为 NULL，
受影响用户需管理员重置密码。

Revision ID: 2026_10_23_0001
Revises: 2026_04_18_0001
Create Date: 2026-10-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import quoted_name


# revision identifiers, used by Alembic.
revision = '2026_10_23_0001'
down_revision = '2026_04_18_0001'
branch_labels = None
depends_on = None

# 需要 add dept_id 的业务表（索引名与模型列级 index=True 生成的名字对齐）
_BIZ_TABLES = [
    'requirements',
    'projects',
    'issues',
    'knowledge_bases',
    'documents',
    'tasks',
    'agent_tasks',
]


def _create_user_center_tables() -> None:
    """建用户中心 9 张表（先主表后关联表，字段与模型零漂移）"""
    # ---- department（部门，树形物化路径） ----
    op.create_table(
        'department',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('parent_id', sa.String(36), nullable=True, comment='父部门 ID，根为 NULL'),
        sa.Column('name', sa.String(100), nullable=False, comment='部门名称'),
        sa.Column('path', sa.String(500), nullable=False, comment='物化路径'),
        sa.Column('sort', sa.Integer(), nullable=False, comment='排序号'),
        sa.Column('status', sa.SmallInteger(), nullable=False, comment='状态：1 启用 0 禁用'),
        sa.Column('dingtalk_dept_id', sa.String(64), nullable=True, comment='钉钉部门 ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.ForeignKeyConstraint(
            ['parent_id'], ['department.id'],
            name='fk_department_parent_id_department',
        ),
    )
    op.create_index('ix_department_path', 'department', ['path'], unique=False)
    op.create_index('uq_department_dingtalk_dept_id', 'department', ['dingtalk_dept_id'], unique=True)

    # ---- position（岗位；position 是 MySQL 关键字，显式加引号） ----
    position_tbl = op.create_table(
        quoted_name('position', True),
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False, comment='岗位名称'),
        sa.Column('dingtalk_job_id', sa.String(64), nullable=True, comment='钉钉岗位 ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
    )
    op.create_index('uq_position_dingtalk_job_id', quoted_name('position', True), ['dingtalk_job_id'], unique=True)

    # ---- user_dept（用户-部门多对多，复合主键） ----
    op.create_table(
        'user_dept',
        sa.Column('user_id', sa.String(36), primary_key=True, comment='用户 ID'),
        sa.Column('dept_id', sa.String(36), primary_key=True, comment='部门 ID'),
        sa.Column('is_primary', sa.Boolean(), nullable=False, comment='是否主部门'),
        sa.Column('position_id', sa.String(36), nullable=True, comment='岗位 ID'),
        sa.ForeignKeyConstraint(
            ['user_id'], ['user.id'], ondelete='CASCADE',
            name='fk_user_dept_user_id_user',
        ),
        sa.ForeignKeyConstraint(
            ['dept_id'], ['department.id'], ondelete='CASCADE',
            name='fk_user_dept_dept_id_department',
        ),
        sa.ForeignKeyConstraint(
            ['position_id'], [position_tbl.c.id],
            name='fk_user_dept_position_id_position',
        ),
    )

    # ---- role（角色） ----
    op.create_table(
        'role',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(50), nullable=False, comment='角色编码'),
        sa.Column('name', sa.String(100), nullable=False, comment='角色名称'),
        sa.Column('description', sa.String(255), nullable=True, comment='角色描述'),
        sa.Column('data_scope', sa.String(20), nullable=False, comment='数据范围：ALL/DEPT_AND_CHILD/DEPT/SELF/CUSTOM'),
        sa.Column('is_system', sa.Boolean(), nullable=False, comment='是否系统预置角色'),
        sa.Column('status', sa.SmallInteger(), nullable=False, comment='状态：1 启用 0 禁用'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
    )
    op.create_index('uq_role_code', 'role', ['code'], unique=True)

    # ---- permission（权限点字典） ----
    op.create_table(
        'permission',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('code', sa.String(100), nullable=False, comment='权限编码'),
        sa.Column('name', sa.String(100), nullable=False, comment='权限名称'),
        sa.Column('type', sa.String(10), nullable=False, comment='类型：menu/button'),
        sa.Column('route_key', sa.String(100), nullable=True, comment='menu 类型对应前端路由 name'),
        sa.Column('status', sa.SmallInteger(), nullable=False, comment='状态：1 启用 0 禁用'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
    )
    op.create_index('uq_permission_code', 'permission', ['code'], unique=True)

    # ---- role_permission（角色-权限关联，复合主键） ----
    op.create_table(
        'role_permission',
        sa.Column('role_id', sa.String(36), primary_key=True, comment='角色 ID'),
        sa.Column('permission_id', sa.String(36), primary_key=True, comment='权限 ID'),
        sa.ForeignKeyConstraint(
            ['role_id'], ['role.id'], ondelete='CASCADE',
            name='fk_role_permission_role_id_role',
        ),
        sa.ForeignKeyConstraint(
            ['permission_id'], ['permission.id'], ondelete='CASCADE',
            name='fk_role_permission_permission_id_permission',
        ),
    )

    # ---- user_role（用户-角色关联，复合主键） ----
    op.create_table(
        'user_role',
        sa.Column('user_id', sa.String(36), primary_key=True, comment='用户 ID'),
        sa.Column('role_id', sa.String(36), primary_key=True, comment='角色 ID'),
        sa.ForeignKeyConstraint(
            ['user_id'], ['user.id'], ondelete='CASCADE',
            name='fk_user_role_user_id_user',
        ),
        sa.ForeignKeyConstraint(
            ['role_id'], ['role.id'], ondelete='CASCADE',
            name='fk_user_role_role_id_role',
        ),
    )

    # ---- role_dept（角色-部门关联，CUSTOM 数据范围用，复合主键） ----
    op.create_table(
        'role_dept',
        sa.Column('role_id', sa.String(36), primary_key=True, comment='角色 ID'),
        sa.Column('dept_id', sa.String(36), primary_key=True, comment='部门 ID'),
        sa.ForeignKeyConstraint(
            ['role_id'], ['role.id'], ondelete='CASCADE',
            name='fk_role_dept_role_id_role',
        ),
        sa.ForeignKeyConstraint(
            ['dept_id'], ['department.id'], ondelete='CASCADE',
            name='fk_role_dept_dept_id_department',
        ),
    )

    # ---- refresh_token（刷新令牌，只存 SHA-256 哈希） ----
    op.create_table(
        'refresh_token',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False, comment='用户 ID'),
        sa.Column('token_hash', sa.String(64), nullable=False, comment='Token SHA-256 哈希'),
        sa.Column('expires_at', sa.DateTime(), nullable=False, comment='过期时间'),
        sa.Column('revoked_at', sa.DateTime(), nullable=True, comment='吊销时间'),
        sa.Column('user_agent', sa.String(255), nullable=True, comment='客户端 User-Agent'),
        sa.Column('ip', sa.String(45), nullable=True, comment='客户端 IP'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('last_used_at', sa.DateTime(), nullable=True, comment='最后使用时间'),
        sa.ForeignKeyConstraint(
            ['user_id'], ['user.id'], ondelete='CASCADE',
            name='fk_refresh_token_user_id_user',
        ),
    )
    op.create_index('ix_refresh_token_user_id', 'refresh_token', ['user_id'], unique=False)
    op.create_index('ix_refresh_token_token_hash', 'refresh_token', ['token_hash'], unique=True)


def _backfill_user_data() -> None:
    """在线模式回填 user.username / user.password_hash（离线 --sql 模式跳过）"""
    from alembic import context

    if context.is_offline_mode():
        # 离线模式没有连接，无法逐行回填，跳过
        #（离线生成的 SQL 需人工执行回填段，或直接在线模式跑）
        return

    from passlib.context import CryptContext

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    conn = op.get_bind()

    # 1) username 回填：优先 jnpf_account，为空则 name；重名追加 _<n> 序号保证唯一
    #    判重统一 lower() 归一化：MySQL 默认 ci collation 的唯一索引不区分大小写，
    #    大小写敏感判重会让 'Zhang'/'zhang' 同时通过，建索引时 duplicate key 中断
    existing = {
        row[0].lower()
        for row in conn.execute(
            sa.text("SELECT DISTINCT username FROM user WHERE username IS NOT NULL AND username != ''")
        ).fetchall()
    }
    rows = conn.execute(
        sa.text("SELECT id, name, jnpf_account FROM user WHERE username IS NULL OR username = ''")
    ).fetchall()
    for row_id, name, jnpf_account in rows:
        base = (jnpf_account or '').strip() or (name or '').strip()
        if not base:
            # 既无账号也无姓名，用主键兜底保证非空
            base = f"user_{row_id}"
        # username 列宽 50，为重名序号预留余量
        base = base[:45]
        candidate = base
        n = 1
        while candidate.lower() in existing:
            n += 1
            candidate = f"{base}_{n}"
        existing.add(candidate.lower())
        conn.execute(
            sa.text("UPDATE user SET username = :username WHERE id = :row_id"),
            {"username": candidate, "row_id": row_id},
        )

    # 2) password_hash 回填：password 非空行 bcrypt 加密后清空明文
    #    hash 失败的行置 must_change_password=1，走管理员重置流程
    rows = conn.execute(
        sa.text("SELECT id, password FROM user WHERE password IS NOT NULL AND password != ''")
    ).fetchall()
    for row_id, plain in rows:
        try:
            hashed = pwd_context.hash(plain)
            conn.execute(
                sa.text("UPDATE user SET password_hash = :h, password = NULL WHERE id = :row_id"),
                {"h": hashed, "row_id": row_id},
            )
        except Exception:
            conn.execute(
                sa.text(
                    "UPDATE user SET password_hash = NULL, must_change_password = 1, "
                    "password = NULL WHERE id = :row_id"
                ),
                {"row_id": row_id},
            )


def upgrade() -> None:
    # ===== 1. 用户中心 9 张表 =====
    _create_user_center_tables()

    # ===== 2. user 表变更：add 新列（bool/int 带 server_default，存量行补默认） =====
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('username', sa.String(50), nullable=True, comment='登录用户名（本地认证）'))
        batch_op.add_column(sa.Column('password_hash', sa.String(255), nullable=True, comment='密码哈希'))
        batch_op.add_column(sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.text('0'), comment='是否强制下次登录修改密码'))
        batch_op.add_column(sa.Column('token_version', sa.Integer(), nullable=False, server_default=sa.text('0'), comment='token 版本号（用于批量吊销 JWT）'))
        batch_op.add_column(sa.Column('dingtalk_user_id', sa.String(64), nullable=True, comment='钉钉用户 ID'))
        batch_op.add_column(sa.Column('failed_attempts', sa.Integer(), nullable=False, server_default=sa.text('0'), comment='连续登录失败次数'))
        batch_op.add_column(sa.Column('locked_until', sa.DateTime(), nullable=True, comment='账号锁定截止时间'))

    # ===== 2.1 数据回填（在线模式；需在建唯一索引之前完成，保证 username 唯一） =====
    _backfill_user_data()

    # ===== 2.2 唯一索引（与模型 __table_args__ 一致） =====
    op.create_index('uq_user_username', 'user', ['username'], unique=True)
    op.create_index('uq_user_dingtalk_user_id', 'user', ['dingtalk_user_id'], unique=True)

    # ===== 2.3 drop 旧列（password 明文已回填为 hash；jwt_token_fingerprint 模型已无） =====
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('password')
        batch_op.drop_column('jwt_token_fingerprint')

    # ===== 3. 业务表 add dept_id（String(36) nullable + 索引） =====
    for table in _BIZ_TABLES:
        with op.batch_alter_table(table) as batch_op:
            batch_op.add_column(
                sa.Column('dept_id', sa.String(36), nullable=True, comment='部门归属快照（创建时所属部门）')
            )
        op.create_index(f'ix_{table}_dept_id', table, ['dept_id'], unique=False)


def downgrade() -> None:
    # ===== 3. 反向：drop 业务表 dept_id 索引+列 =====
    for table in _BIZ_TABLES:
        op.drop_index(f'ix_{table}_dept_id', table_name=table)
        with op.batch_alter_table(table) as batch_op:
            batch_op.drop_column('dept_id')

    # ===== 2. 反向：user 表 =====
    # drop 唯一索引
    op.drop_index('uq_user_dingtalk_user_id', table_name='user')
    op.drop_index('uq_user_username', table_name='user')

    # drop 新增列
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('locked_until')
        batch_op.drop_column('failed_attempts')
        batch_op.drop_column('dingtalk_user_id')
        batch_op.drop_column('token_version')
        batch_op.drop_column('must_change_password')
        batch_op.drop_column('password_hash')
        batch_op.drop_column('username')

    # 重建旧列。注意：password_hash 不可逆，重建的 password 全部为 NULL，
    # 受影响用户需管理员重置密码（见文件头注释）
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('password', sa.String(255), nullable=True, comment='密码（JNPF 用户不需要）'))
        batch_op.add_column(sa.Column('jwt_token_fingerprint', sa.String(64), nullable=True, comment='JWT token 的 SHA-256 哈希（用于验证但不泄露token）'))

    # ===== 1. 反向：drop 9 张新表（先关联表后主表） =====
    op.drop_table('refresh_token')
    op.drop_table('role_dept')
    op.drop_table('user_role')
    op.drop_table('role_permission')
    op.drop_table('permission')
    op.drop_table('role')
    op.drop_table('user_dept')
    op.drop_table(quoted_name('position', True))
    op.drop_table('department')
