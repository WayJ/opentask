"""merge_heads

Revision ID: 105845b0ee19
Revises: 514b5d1f86fa, 202602250400
Create Date: 2026-02-25 04:10:16.660902

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '105845b0ee19'
down_revision: Union[str, None] = ('514b5d1f86fa', '202602250400')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
