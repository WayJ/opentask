"""issue_timeline audit actions: CF/cycle/estimate/project (E41)

Revision ID: h4c5d6e7f8a2
Revises: g3b4c5d6e7f1
"""
from __future__ import annotations

from alembic import op

revision = "h4c5d6e7f8a2"
down_revision = "g3b4c5d6e7f1"
branch_labels = None
depends_on = None

_NEW_VALUES = (
    "custom_field_changed",
    "cycle_changed",
    "estimate_changed",
    "project_changed",
)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # PG: ADD VALUE cannot run inside a transaction block on older versions;
    # use IF NOT EXISTS (PG 9.3+ for ADD VALUE; IF NOT EXISTS since PG 9.1 / 15).
    for val in _NEW_VALUES:
        op.execute(f"ALTER TYPE timeline_action ADD VALUE IF NOT EXISTS '{val}'")


def downgrade() -> None:
    # PG cannot easily drop enum values; leave as no-op.
    pass
