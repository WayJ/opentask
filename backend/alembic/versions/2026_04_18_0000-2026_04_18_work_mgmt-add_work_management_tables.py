"""add work management tables

Revision ID: 2026_04_18_work_mgmt
Revises: f6a7b8c9d0e1
Create Date: 2026-04-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_04_18_work_mgmt'
down_revision: Union[str, None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 研发组表
    op.create_table(
        'rd_groups',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('director_id', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('leader_id', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('status', sa.Enum('active', 'inactive', name='rd_group_status'), nullable=False, default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        comment='研发组'
    )

    # 研发组成员表
    op.create_table(
        'rd_group_members',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('group_id', sa.String(36), sa.ForeignKey('rd_groups.id'), nullable=False),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('role', sa.Enum('director', 'leader', 'member', name='rd_group_role'), nullable=False),
        sa.Column('joined_at', sa.DateTime(), nullable=False),
        sa.Index('ix_rd_group_members_group_user', 'group_id', 'user_id'),
        comment='研发组成员'
    )

    # 成本承担项目表
    op.create_table(
        'cost_projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('manager_id', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('status', sa.Enum('active', 'completed', 'archived', name='cost_project_status'), nullable=False, default='active'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Index('ix_cost_projects_code', 'code'),
        comment='成本承担项目'
    )

    # 工作安排表
    op.create_table(
        'work_assignments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('assignee_id', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('assigner_id', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('group_id', sa.String(36), sa.ForeignKey('rd_groups.id'), nullable=False),
        sa.Column('cost_project_id', sa.String(36), sa.ForeignKey('cost_projects.id'), nullable=False),
        sa.Column('deadline', sa.Date(), nullable=False),
        sa.Column('estimated_hours', sa.Numeric(6, 1), nullable=False),
        sa.Column('week_start', sa.Date(), nullable=False, index=True),
        sa.Column('status', sa.Enum('not_started', 'in_progress', 'completed', 'blocked', name='work_status'), nullable=False, default='not_started'),
        sa.Column('related_type', sa.Enum('requirement', 'issue', name='related_type'), nullable=True),
        sa.Column('related_id', sa.String(36), nullable=True),
        sa.Column('quality', sa.Enum('high', 'low', 'unknown', name='quality_level'), nullable=False, default='unknown'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Index('ix_work_assignments_assignee', 'assignee_id'),
        sa.Index('ix_work_assignments_week', 'week_start'),
        sa.Index('ix_work_assignments_deadline_status', 'deadline', 'status'),
        comment='工作安排'
    )

    # 工作反馈表
    op.create_table(
        'work_feedback',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('assignment_id', sa.String(36), sa.ForeignKey('work_assignments.id'), nullable=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('feedback_date', sa.Date(), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('not_started', 'in_progress', 'completed', 'blocked', name='work_status'), nullable=False),
        sa.Column('is_planned', sa.Boolean(), nullable=False, default=True),
        sa.Column('unplanned_type', sa.Enum('issue_created', 'issue_resolved', 'req_created', 'req_completed', 'other', name='unplanned_type'), nullable=True),
        sa.Column('unplanned_related_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Index('ix_work_feedback_user_date', 'user_id', 'feedback_date'),
        comment='工作反馈'
    )

    # 工作安排附件表
    op.create_table(
        'work_assignment_attachments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('assignment_id', sa.String(36), sa.ForeignKey('work_assignments.id'), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('uploaded_by', sa.String(36), sa.ForeignKey('user.id'), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(), nullable=False),
        sa.Index('ix_work_attachments_assignment', 'assignment_id'),
        comment='工作安排附件'
    )


def downgrade() -> None:
    op.drop_table('work_assignment_attachments')
    op.drop_table('work_feedback')
    op.drop_table('work_assignments')
    op.drop_table('cost_projects')
    op.drop_table('rd_group_members')
    op.drop_table('rd_groups')
    # 注意：MySQL ENUM 类型在表删除后会自动清理，无需手动删除
