"""
创建 Agent 表的数据库迁移
Revision ID: 2026_03_16_1850
Revises: 2026_03_16_1700
Create Time: 2026-03-16 18:50
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision = '2026_03_16_1850'
down_revision = '2026_03_16_1700'


def upgrade():
    """创建 Agent 表"""
    op.create_table(
        'agents',
        sa.Column('agent_id', sa.String(255), nullable=False, comment='Agent ID'),
        sa.Column('agent_type', sa.String(100), nullable=False, comment='Agent 类型'),
        sa.Column('agent_name', sa.String(255), nullable=False, comment='Agent 显示名称'),
        sa.Column('capabilities', sa.JSON(), nullable=True, comment='Agent 能力列表'),
        sa.Column('model', sa.String(100), nullable=True, comment='使用的 AI 模型'),

        # 状态字段
        sa.Column('status', sa.String(50), nullable=False, server_default='registered', comment='Agent 状态'),
        sa.Column('previous_status', sa.String(50), nullable=True, comment='上一个状态'),

        # 连接信息
        sa.Column('connected_at', sa.DateTime(), nullable=True, comment='首次连接时间'),
        sa.Column('last_heartbeat', sa.DateTime(), nullable=True, comment='最后心跳时间'),
        sa.Column('disconnected_at', sa.DateTime(), nullable=True, comment='断开连接时间'),

        # 统计信息
        sa.Column('total_tasks_handled', sa.Integer(), nullable=False, server_default='0', comment='总处理任务数'),
        sa.Column('successful_tasks', sa.Integer(), nullable=False, server_default='0', comment='成功任务数'),
        sa.Column('failed_tasks', sa.Integer(), nullable=False, server_default='0', comment='失败任务数'),
        sa.Column('total_execution_time', sa.Integer(), nullable=False, server_default='0', comment='总执行时间（秒）'),

        # 当前任务
        sa.Column('current_task_id', sa.String(255), nullable=True, comment='当前正在处理的任务 ID'),
        sa.Column('current_task_started_at', sa.DateTime(), nullable=True, comment='当前任务开始时间'),

        # 健康监控
        sa.Column('heartbeat_misses', sa.Integer(), nullable=False, server_default='0', comment='心跳丢失次数'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0', comment='错误次数'),
        sa.Column('last_error', sa.Text(), nullable=True, comment='最后错误信息'),
        sa.Column('last_error_at', sa.DateTime(), nullable=True, comment='最后错误时间'),

        # 生命周期管理
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1', comment='是否激活'),
        sa.Column('retired_at', sa.DateTime(), nullable=True, comment='退役时间'),
        sa.Column('retired_by', sa.String(255), nullable=True, comment='退役操作者'),
        sa.Column('retire_reason', sa.Text(), nullable=True, comment='退役原因'),

        # 元数据和时间戳
        sa.Column('metadata', sa.JSON(), nullable=True, comment='其他自定义信息'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')),

        sa.PrimaryKeyConstraint('agent_id'),
        mysql_charset='utf8mb4',
        mysql_collate='utf8mb4_unicode_ci'
    )

    # 创建索引
    op.create_index('idx_agent_type', 'agents', ['agent_type'])
    op.create_index('idx_agent_status', 'agents', ['status'])
    op.create_index('idx_agent_last_heartbeat', 'agents', ['last_heartbeat'])
    op.create_index('idx_agent_is_active', 'agents', ['is_active'])


def downgrade():
    """删除 Agent 表"""
    op.drop_table('agents')
