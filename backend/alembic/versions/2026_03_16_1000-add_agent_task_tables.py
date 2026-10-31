"""
add agent task tables

添加 Agent 任务管理相关的数据库表：
- agent_tasks: Agent 任务表
- agent_wallets: Agent 钱包表
- agent_transactions: Agent 交易流水表

Revision ID: 2026_03_16_1000
Revises: 2026_03_13_1000
Create Date: 2026-03-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '2026_03_16_1000'
down_revision = '2026_03_13_1000'  # 链接到最新的迁移
branch_labels = None
depends_on = None


def upgrade():
    """创建 Agent Task 相关表"""

    # ============================================
    # 1. 创建 agent_tasks 表
    # ============================================

    op.create_table(
        'agent_tasks',
        sa.Column('task_id', sa.String(36), primary_key=True, comment='任务 ID'),
        sa.Column('title', sa.String(255), nullable=False, comment='任务标题'),
        sa.Column('description', sa.Text(), nullable=True, comment='任务描述'),
        sa.Column('priority', sa.Enum('low', 'medium', 'high', 'urgent', name='agent_task_priority'),
                  nullable=False, default='medium', comment='优先级'),
        sa.Column('assignee', sa.String(255), nullable=True, comment='分配给哪个 Agent'),
        sa.Column('deadline', sa.DateTime(), nullable=True, comment='截止时间'),
        sa.Column('metadata', sa.JSON(), nullable=True, comment='元数据'),
        sa.Column('requirements', sa.JSON(), nullable=True, comment='需求列表'),
        sa.Column('acceptance_criteria', sa.JSON(), nullable=True, comment='验收标准'),
        sa.Column('reward', sa.Integer(), nullable=False, default=0, comment='金币奖励'),
        sa.Column('status', sa.Enum('pending', 'assigned', 'in_progress', 'completed', 'failed', 'cancelled', 'blocked',
                                    name='agent_task_status'), nullable=False, default='pending', comment='任务状态'),
        sa.Column('progress_percentage', sa.Integer(), nullable=False, default=0, comment='进度百分比 (0-100)'),
        sa.Column('current_step', sa.String(500), nullable=False, default='', comment='当前步骤描述'),
        sa.Column('result', sa.JSON(), nullable=True, comment='执行结果'),
        sa.Column('error', sa.JSON(), nullable=True, comment='错误信息'),
        sa.Column('logs', sa.JSON(), nullable=True, comment='日志列表'),
        sa.Column('progress_history', sa.JSON(), nullable=True, comment='进度历史记录'),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True, comment='执行时间（毫秒）'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        sa.Column('completed_at', sa.DateTime(), nullable=True, comment='完成时间'),
        comment='Agent 任务表'
    )

    # 创建索引
    op.create_index('idx_agent_tasks_status', 'agent_tasks', ['status'])
    op.create_index('idx_agent_tasks_priority', 'agent_tasks', ['priority'])
    op.create_index('idx_agent_tasks_assignee', 'agent_tasks', ['assignee'])
    op.create_index('idx_agent_tasks_created_at', 'agent_tasks', ['created_at'])
    op.create_index('idx_agent_tasks_updated_at', 'agent_tasks', ['updated_at'])
    op.create_index('idx_agent_tasks_status_priority', 'agent_tasks', ['status', 'priority'])
    op.create_index('idx_agent_tasks_assignee_status', 'agent_tasks', ['assignee', 'status'])

    # ============================================
    # 2. 创建 agent_wallets 表
    # ============================================

    op.create_table(
        'agent_wallets',
        sa.Column('agent_id', sa.String(255), primary_key=True, comment='Agent ID'),
        sa.Column('balance', sa.Integer(), nullable=False, default=0, comment='当前余额（金币）'),
        sa.Column('total_earned', sa.Integer(), nullable=False, default=0, comment='累计获得金币'),
        sa.Column('total_spent', sa.Integer(), nullable=False, default=0, comment='累计消费金币'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, comment='更新时间'),
        comment='Agent 钱包表'
    )

    # 创建索引
    op.create_index('idx_agent_wallets_balance', 'agent_wallets', ['balance'])

    # ============================================
    # 3. 创建 agent_transactions 表
    # ============================================

    op.create_table(
        'agent_transactions',
        sa.Column('id', sa.String(36), primary_key=True, comment='交易 ID'),
        sa.Column('agent_id', sa.String(255), sa.ForeignKey('agent_wallets.agent_id', ondelete='CASCADE'),
                  nullable=False, comment='Agent ID'),
        sa.Column('amount', sa.Integer(), nullable=False, comment='交易金额（正数为收入，负数为支出）'),
        sa.Column('balance_after', sa.Integer(), nullable=False, comment='交易后余额'),
        sa.Column('transaction_type', sa.Enum('task_reward', 'task_penalty', 'system_adjustment', 'manual',
                                              name='transaction_type'), nullable=False, comment='交易类型'),
        sa.Column('description', sa.Text(), nullable=False, comment='交易描述'),
        sa.Column('related_task_id', sa.String(36), nullable=True, comment='关联任务 ID'),
        sa.Column('created_at', sa.DateTime(), nullable=False, comment='创建时间'),
        comment='Agent 交易流水表'
    )

    # 创建索引
    op.create_index('idx_agent_transactions_agent', 'agent_transactions', ['agent_id'])
    op.create_index('idx_agent_transactions_type', 'agent_transactions', ['transaction_type'])
    op.create_index('idx_agent_transactions_task', 'agent_transactions', ['related_task_id'])
    op.create_index('idx_agent_transactions_created_at', 'agent_transactions', ['created_at'])
    op.create_index('idx_agent_transactions_agent_created', 'agent_transactions', ['agent_id', 'created_at'])


def downgrade():
    """回滚迁移"""

    # 删除 agent_transactions 表
    try:
        op.drop_index('idx_agent_transactions_agent_created', 'agent_transactions')
    except Exception:
        pass

    try:
        op.drop_index('idx_agent_transactions_created_at', 'agent_transactions')
    except Exception:
        pass

    try:
        op.drop_index('idx_agent_transactions_task', 'agent_transactions')
    except Exception:
        pass

    try:
        op.drop_index('idx_agent_transactions_type', 'agent_transactions')
    except Exception:
        pass

    try:
        op.drop_index('idx_agent_transactions_agent', 'agent_transactions')
    except Exception:
        pass

    try:
        op.drop_table('agent_transactions')
    except Exception:
        pass

    # 删除 agent_wallets 表
    try:
        op.drop_index('idx_agent_wallets_balance', 'agent_wallets')
    except Exception:
        pass

    try:
        op.drop_table('agent_wallets')
    except Exception:
        pass

    # 删除 agent_tasks 表
    try:
        op.drop_index('idx_agent_tasks_assignee_status', 'agent_tasks')
    except Exception:
        pass

    try:
        op.drop_index('idx_agent_tasks_status_priority', 'agent_tasks')
    except Exception:
        pass

    try:
        op.drop_index('idx_agent_tasks_updated_at', 'agent_tasks')
    except Exception:
        pass

    try:
        op.drop_index('idx_agent_tasks_created_at', 'agent_tasks')
    except Exception:
        pass

    try:
        op.drop_index('idx_agent_tasks_assignee', 'agent_tasks')
    except Exception:
        pass

    try:
        op.drop_index('idx_agent_tasks_priority', 'agent_tasks')
    except Exception:
        pass

    try:
        op.drop_index('idx_agent_tasks_status', 'agent_tasks')
    except Exception:
        pass

    try:
        op.drop_table('agent_tasks')
    except Exception:
        pass
