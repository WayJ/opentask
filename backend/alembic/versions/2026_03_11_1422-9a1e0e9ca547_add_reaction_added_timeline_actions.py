"""add_reaction_added_timeline_actions

Revision ID: 9a1e0e9ca547
Revises: 44ee59a7e62c
Create Date: 2026-03-11 14:22:36.031458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a1e0e9ca547'
down_revision: Union[str, None] = '44ee59a7e62c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 修改 issue_timeline 表的 action_type ENUM，添加 reaction_added 和 reaction_removed
    # MySQL 中修改 ENUM 需要使用 ALTER TABLE ... MODIFY COLUMN
    op.execute("""
        ALTER TABLE issue_timeline
        MODIFY COLUMN action_type ENUM(
            'created',
            'updated',
            'commented',
            'status_changed',
            'assigned',
            'priority_changed',
            'due_date_changed',
            'relation_added',
            'relation_removed',
            'attachment_added',
            'attachment_removed',
            'label_added',
            'label_removed',
            'resolved',
            'closed',
            'reopened',
            'reaction_added',
            'reaction_removed'
        )
        NOT NULL
    """)


def downgrade() -> None:
    # 回滚：移除 reaction_added 和 reaction_removed
    op.execute("""
        ALTER TABLE issue_timeline
        MODIFY COLUMN action_type ENUM(
            'created',
            'updated',
            'commented',
            'status_changed',
            'assigned',
            'priority_changed',
            'due_date_changed',
            'relation_added',
            'relation_removed',
            'attachment_added',
            'attachment_removed',
            'label_added',
            'label_removed',
            'resolved',
            'closed',
            'reopened'
        )
        NOT NULL
    """)
