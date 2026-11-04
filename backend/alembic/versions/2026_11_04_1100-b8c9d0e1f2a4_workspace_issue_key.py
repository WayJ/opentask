"""workspace issue_key + issue_counter + issues.legacy_issue_code (E12-S1)

Revision ID: b8c9d0e1f2a4
Revises: a7b8c9d0e1f3
"""

from __future__ import annotations

import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a4"
down_revision: Union[str, None] = "a7b8c9d0e1f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SLUG_ALNUM = re.compile(r"[^A-Z0-9]")
_ISSUE_YEAR = re.compile(r"^ISSUE\d+-\d+$", re.I)


def _derive(slug: str) -> str:
    raw = _SLUG_ALNUM.sub("", (slug or "").upper())
    if len(raw) >= 2:
        return raw[:6]
    if len(raw) == 1:
        return (raw + "T")[:2]
    return "OT"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    ws_cols = {c["name"] for c in inspector.get_columns("workspaces")}
    issue_cols = {c["name"] for c in inspector.get_columns("issues")}

    if "issue_key" not in ws_cols:
        op.add_column(
            "workspaces",
            sa.Column("issue_key", sa.String(6), nullable=False, server_default="OT"),
        )
    if "issue_counter" not in ws_cols:
        op.add_column(
            "workspaces",
            sa.Column("issue_counter", sa.Integer(), nullable=False, server_default="0"),
        )
    if "legacy_issue_code" not in issue_cols:
        op.add_column(
            "issues",
            sa.Column("legacy_issue_code", sa.String(50), nullable=True),
        )
        op.create_index("ix_issues_legacy_issue_code", "issues", ["legacy_issue_code"])

    # Backfill issue_key uniquely from slug
    rows = bind.execute(sa.text("SELECT id, slug, issue_key FROM workspaces")).fetchall()
    used: set[str] = set()
    for wid, slug, current in rows:
        key = (current or "").strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{2,6}", key) or key in used:
            base = _derive(slug or "")
            key = base
            n = 2
            while key in used:
                suffix = str(n)
                key = (base[: max(2, 6 - len(suffix))] + suffix)[:6]
                n += 1
        used.add(key)
        bind.execute(
            sa.text("UPDATE workspaces SET issue_key = :k WHERE id = :id"),
            {"k": key, "id": wid},
        )

    # Backfill issues per workspace
    for wid, _slug, _k in rows:
        key_row = bind.execute(
            sa.text("SELECT issue_key FROM workspaces WHERE id = :id"),
            {"id": wid},
        ).fetchone()
        key = key_row[0]
        issues = bind.execute(
            sa.text(
                "SELECT id, issue_code FROM issues "
                "WHERE workspace_id = :wid AND COALESCE(is_deleted, false) = false "
                "ORDER BY created_at ASC, id ASC"
            ),
            {"wid": wid},
        ).fetchall()
        counter = 0
        for iid, code in issues:
            counter += 1
            new_code = f"{key}-{counter}"
            legacy = code if _ISSUE_YEAR.match(code or "") else None
            # Avoid unique collisions if somehow already KEY-N matching
            if code == new_code:
                bind.execute(
                    sa.text(
                        "UPDATE issues SET legacy_issue_code = COALESCE(legacy_issue_code, :legacy) "
                        "WHERE id = :id"
                    ),
                    {"legacy": legacy, "id": iid},
                )
                continue
            bind.execute(
                sa.text(
                    "UPDATE issues SET legacy_issue_code = COALESCE(legacy_issue_code, :legacy), "
                    "issue_code = :new_code WHERE id = :id"
                ),
                {"legacy": legacy or code, "new_code": new_code, "id": iid},
            )
        bind.execute(
            sa.text("UPDATE workspaces SET issue_counter = :c WHERE id = :id"),
            {"c": counter, "id": wid},
        )

    # Unique constraint on issue_key
    uqs = {uq["name"] for uq in inspector.get_unique_constraints("workspaces")}
    # re-inspect after adds
    inspector = sa.inspect(bind)
    uqs = {uq["name"] for uq in inspector.get_unique_constraints("workspaces")}
    if "uq_workspaces_issue_key" not in uqs:
        op.create_unique_constraint("uq_workspaces_issue_key", "workspaces", ["issue_key"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    uqs = {uq["name"] for uq in inspector.get_unique_constraints("workspaces")}
    if "uq_workspaces_issue_key" in uqs:
        op.drop_constraint("uq_workspaces_issue_key", "workspaces", type_="unique")
    issue_cols = {c["name"] for c in inspector.get_columns("issues")}
    if "legacy_issue_code" in issue_cols:
        op.drop_index("ix_issues_legacy_issue_code", table_name="issues")
        op.drop_column("issues", "legacy_issue_code")
    ws_cols = {c["name"] for c in inspector.get_columns("workspaces")}
    if "issue_counter" in ws_cols:
        op.drop_column("workspaces", "issue_counter")
    if "issue_key" in ws_cols:
        op.drop_column("workspaces", "issue_key")
