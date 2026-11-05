"""E78: add timeline_action value 'parent_changed' (no new tables).

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
Create Date: 2026-11-05
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, None] = "c6d7e8f9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE timeline_action ADD VALUE IF NOT EXISTS 'parent_changed'")


def downgrade() -> None:
    # PostgreSQL cannot easily drop enum values; leave as no-op.
    pass
