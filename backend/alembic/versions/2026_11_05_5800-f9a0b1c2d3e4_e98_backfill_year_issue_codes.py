"""E98: backfill ISSUE{year}-N primary codes to KEY-N (keep legacy)

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3

Only rewrites rows whose current issue_code matches ^ISSUE[0-9]{4}-[0-9]+$.
Does not reshuffle existing KEY-N. Skips when legacy_issue_code is set to a
different value. Orphans without a reliable creator writable WS are skipped
(not deleted). Idempotent.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f9a0b1c2d3e4"
down_revision: Union[str, None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.e98_backfill")

_YEAR_CODE = re.compile(r"^ISSUE[0-9]{4}-[0-9]+$")


def backfill_year_issue_codes(bind) -> dict[str, int]:
    """Portable backfill (PG/SQLite). Safe on empty DB. Idempotent."""
    stats = {
        "rewritten": 0,
        "skipped_legacy_conflict": 0,
        "skipped_orphan": 0,
        "bound_orphan": 0,
    }
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "issues" not in tables or "workspaces" not in tables:
        return stats
    issue_cols = {c["name"] for c in inspector.get_columns("issues")}
    if "legacy_issue_code" not in issue_cols or "issue_code" not in issue_cols:
        return stats

    order_nulls = "NULLS LAST" if bind.dialect.name == "postgresql" else ""
    raw = bind.execute(
        sa.text(
            f"SELECT id, issue_code, legacy_issue_code, workspace_id, created_by, created_at "
            f"FROM issues WHERE issue_code LIKE 'ISSUE%' "
            f"ORDER BY created_at ASC {order_nulls}, id ASC"
        )
    ).fetchall()
    year_rows = [r for r in raw if _YEAR_CODE.match(r[1] or "")]

    by_ws: dict[str, list[Any]] = {}
    for row in year_rows:
        iid, code, legacy, wid, created_by, _created_at = row
        if legacy and legacy != code:
            stats["skipped_legacy_conflict"] += 1
            continue
        if not wid:
            wid = _try_bind_orphan(bind, created_by)
            if not wid:
                stats["skipped_orphan"] += 1
                logger.info("E98 skip orphan issue %s (no reliable WS)", iid)
                continue
            bind.execute(
                sa.text("UPDATE issues SET workspace_id = :wid WHERE id = :id"),
                {"wid": wid, "id": iid},
            )
            stats["bound_orphan"] += 1
        by_ws.setdefault(wid, []).append((iid, code, legacy))

    for wid, items in by_ws.items():
        ws = bind.execute(
            sa.text("SELECT issue_key, issue_counter FROM workspaces WHERE id = :id"),
            {"id": wid},
        ).fetchone()
        if ws is None:
            stats["skipped_orphan"] += len(items)
            continue
        issue_key, counter = ws[0], int(ws[1] or 0)
        for iid, code, legacy in items:
            counter += 1
            new_code = f"{issue_key}-{counter}"
            new_legacy = legacy if legacy else code
            bind.execute(
                sa.text(
                    "UPDATE issues SET issue_code = :new_code, "
                    "legacy_issue_code = :legacy WHERE id = :id"
                ),
                {"new_code": new_code, "legacy": new_legacy, "id": iid},
            )
            stats["rewritten"] += 1
        bind.execute(
            sa.text("UPDATE workspaces SET issue_counter = :c WHERE id = :id"),
            {"c": counter, "id": wid},
        )
    return stats


def _try_bind_orphan(bind, created_by: str | None) -> str | None:
    if not created_by:
        return None
    rows = bind.execute(
        sa.text(
            "SELECT workspace_id FROM workspace_members "
            "WHERE user_id = :uid AND role IN ('owner', 'member')"
        ),
        {"uid": created_by},
    ).fetchall()
    writable = [r[0] for r in rows]
    if len(writable) == 1:
        return writable[0]
    if len(writable) == 0:
        return None
    personal = bind.execute(
        sa.text(
            "SELECT w.id FROM workspaces w "
            "JOIN workspace_members m ON m.workspace_id = w.id "
            "WHERE w.created_by = :uid AND m.user_id = :uid AND m.role = 'owner'"
        ),
        {"uid": created_by},
    ).fetchall()
    personal_ids = [r[0] for r in personal if r[0] in set(writable)]
    if len(personal_ids) == 1:
        return personal_ids[0]
    return None


def upgrade() -> None:
    bind = op.get_bind()
    stats = backfill_year_issue_codes(bind)
    logger.info("E98 backfill stats: %s", stats)


def downgrade() -> None:
    pass
