"""E41：Issue timeline CSV export helpers."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime
from typing import Any, Iterable, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.model import Issue, IssueTimeline
from opentask.models.user.model import UserModel

EXPORT_HARD_CAP = 10000
EXPORT_DEFAULT_LIMIT = 5000

CSV_COLUMNS = [
    "created_at",
    "action_type",
    "user_id",
    "user_name",
    "field_key",
    "from_value",
    "to_value",
    "action_data_json",
]


def _normalize_action_types(raw: Optional[Sequence[str] | str]) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        return parts or None
    out: list[str] = []
    for item in raw:
        if not item:
            continue
        for p in str(item).split(","):
            p = p.strip()
            if p and p not in out:
                out.append(p)
    return out or None


def _scalar_str(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, (str, int, float, bool)):
        return str(v)
    try:
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    except TypeError:
        return str(v)


def _action_type_value(action_type: Any) -> str:
    return getattr(action_type, "value", action_type) if action_type is not None else ""


async def build_timeline_csv(
    db: AsyncSession,
    *,
    workspace_id: str,
    issue_id: Optional[str] = None,
    since: Optional[datetime] = None,
    action_types: Optional[Sequence[str] | str] = None,
    limit: Optional[int] = None,
) -> tuple[bytes, bool]:
    """Build CSV for timeline rows in workspace. Returns (utf-8 bytes, truncated)."""
    lim = EXPORT_DEFAULT_LIMIT if limit is None else int(limit)
    if lim < 1:
        lim = 1
    if lim > EXPORT_HARD_CAP:
        lim = EXPORT_HARD_CAP

    types = _normalize_action_types(action_types)

    q = (
        select(IssueTimeline)
        .join(Issue, Issue.id == IssueTimeline.issue_id)
        .where(
            Issue.workspace_id == workspace_id,
            Issue.is_deleted == False,  # noqa: E712
        )
    )
    if issue_id:
        q = q.where(IssueTimeline.issue_id == issue_id)
    if since is not None:
        q = q.where(IssueTimeline.created_at >= since)
    if types:
        q = q.where(IssueTimeline.action_type.in_(types))

    q = q.order_by(IssueTimeline.created_at.desc()).limit(lim + 1)
    result = await db.execute(q)
    rows: list[IssueTimeline] = list(result.scalars().all())
    truncated = len(rows) > lim
    rows = rows[:lim]

    user_ids = list({r.user_id for r in rows if r.user_id})
    name_map: dict[str, str] = {}
    if user_ids:
        # UserModel.id may be UUID — compare as str
        ures = await db.execute(select(UserModel).where(UserModel.id.in_(user_ids)))
        for u in ures.scalars().all():
            name_map[str(u.id)] = u.name or getattr(u, "sso_name", None) or ""

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for r in rows:
        ad = r.action_data or {}
        field_key = ad.get("fieldKey") or ad.get("field_key") or ""
        from_v = ad.get("from", "")
        to_v = ad.get("to", "")
        writer.writerow(
            {
                "created_at": r.created_at.isoformat() if r.created_at else "",
                "action_type": _action_type_value(r.action_type),
                "user_id": r.user_id or "",
                "user_name": name_map.get(str(r.user_id or ""), ""),
                "field_key": field_key,
                "from_value": _scalar_str(from_v) if from_v != "" or "from" in ad else "",
                "to_value": _scalar_str(to_v) if to_v != "" or "to" in ad else "",
                "action_data_json": json.dumps(ad, ensure_ascii=False, separators=(",", ":"))
                if ad
                else "",
            }
        )
    return buf.getvalue().encode("utf-8"), truncated
