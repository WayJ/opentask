"""E98: year-code backfill — SUPERSEDED by E99 (documented no-op)

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3

E99 (Way pt226u/pt227u): no historical environments; stock year→KEY-N migration
behavior is removed. Revision id is retained so DBs already stamped at f9a0 remain
chain-stable. E99 revision g0a1b2c3d4e5 drops issues.legacy_issue_code.
"""

from __future__ import annotations

import logging
from typing import Sequence, Union

from alembic import op  # noqa: F401  # kept for alembic env parity

revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.e98_backfill")


def backfill_year_issue_codes(bind) -> dict[str, int]:
    """No-op (E99). Previously rewrote ISSUE{year}-N → KEY-N + legacy.

    Kept as an importable symbol so directed tests can assert the no-op contract.
    """
    _ = bind
    return {
        "rewritten": 0,
        "skipped_legacy_conflict": 0,
        "skipped_orphan": 0,
        "bound_orphan": 0,
        "noop": 1,
    }


def upgrade() -> None:
    logger.info(
        "E98 backfill superseded by E99; no stock migration (revision retained as no-op)"
    )


def downgrade() -> None:
    pass
