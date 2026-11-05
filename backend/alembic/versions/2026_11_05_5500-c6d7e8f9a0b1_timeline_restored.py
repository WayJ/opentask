"""E77: add timeline_action value 'restored' (no new tables).

Revision ID: c6d7e8f9a0b1
Revises: b5c6d7e8f9a0
Create Date: 2026-11-05
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "c6d7e8f9a0b1"
down_revision: Union[str, None] = "b5c6d7e8f9a0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE timeline_action ADD VALUE IF NOT EXISTS 'restored'")


def downgrade() -> None:
    # PostgreSQL cannot easily drop enum values; leave as no-op.
    pass
