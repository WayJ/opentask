"""E41/E47：Issue timeline CSV export + shared activity query helpers."""
from __future__ import annotations

import base64
import csv
import io
import json
from datetime import datetime
from typing import Any, Optional, Sequence

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.model import Issue, IssueTimeline
from opentask.models.user.model import UserModel

EXPORT_HARD_CAP = 10000
EXPORT_DEFAULT_LIMIT = 5000

ACTIVITY_DEFAULT_LIMIT = 50
ACTIVITY_HARD_CAP = 200

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


def clamp_activity_limit(limit: Optional[int]) -> int:
    """Clamp page size to [1, ACTIVITY_HARD_CAP]; default ACTIVITY_DEFAULT_LIMIT."""
    if limit is None:
        return ACTIVITY_DEFAULT_LIMIT
    try:
        lim = int(limit)
    except (TypeError, ValueError):
        return ACTIVITY_DEFAULT_LIMIT
    if lim < 1:
        return 1
    if lim > ACTIVITY_HARD_CAP:
        return ACTIVITY_HARD_CAP
    return lim



def clamp_unread_count(raw: int, *, hard_cap: int = 99) -> tuple[int, bool]:
    """Clamp unread badge; returns (display_count, capped)."""
    try:
        n = int(raw)
    except (TypeError, ValueError):
        return 0, False
    if n < 0:
        n = 0
    if n > hard_cap:
        return hard_cap, True
    return n, False


def build_reaction_summary(
    emoji_users: dict[str, list[str]],
    *,
    viewer_id: str | None = None,
) -> list[dict[str, Any]]:
    """Normalize emoji→user_ids into Activity reaction chips."""
    out: list[dict[str, Any]] = []
    for emoji, users in sorted(emoji_users.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        ids = [str(u) for u in (users or []) if u]
        out.append(
            {
                "emoji": emoji,
                "count": len(ids),
                "myReacted": bool(viewer_id and str(viewer_id) in ids),
            }
        )
    return out


def extract_comment_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    cid = payload.get("comment_id") or payload.get("commentId")
    if cid is None:
        return None
    s = str(cid).strip()
    if not s or s.lower() in {"none", "null"}:
        return None
    return s


def encode_activity_cursor(created_at: datetime, row_id: str) -> str:
    """Opaque cursor: base64url of ``iso|id``."""
    raw = f"{created_at.isoformat()}|{row_id}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_activity_cursor(cursor: str) -> tuple[datetime, str]:
    """Decode cursor; raises ValueError on bad input."""
    if not cursor or not isinstance(cursor, str):
        raise ValueError("empty cursor")
    pad = "=" * (-len(cursor) % 4)
    try:
        raw = base64.urlsafe_b64decode(cursor + pad).decode("utf-8")
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"invalid cursor encoding: {e}") from e
    if "|" not in raw:
        raise ValueError("invalid cursor payload")
    iso, row_id = raw.split("|", 1)
    if not row_id:
        raise ValueError("invalid cursor id")
    try:
        ts = datetime.fromisoformat(iso)
    except ValueError as e:
        raise ValueError(f"invalid cursor timestamp: {e}") from e
    return ts, row_id


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


async def query_timeline_entries(
    db: AsyncSession,
    *,
    workspace_id: str,
    issue_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    action_types: Optional[Sequence[str] | str] = None,
    actor_id: Optional[str] = None,
    cursor: Optional[tuple[datetime, str]] = None,
    limit: int = EXPORT_DEFAULT_LIMIT,
    watcher_user_id: Optional[str] = None,
) -> list[IssueTimeline]:
    """Shared timeline query (E41 CSV + E47 JSON). Returns up to ``limit`` rows.

    Caller that needs next-page detection should pass ``limit+1``.
    When ``watcher_user_id`` is set (E52), restrict to issues the user watches
    in this workspace via ``issue_watchers``.
    """
    types = _normalize_action_types(action_types)

    q = (
        select(IssueTimeline)
        .join(Issue, Issue.id == IssueTimeline.issue_id)
        .where(
            Issue.workspace_id == workspace_id,
            Issue.is_deleted == False,  # noqa: E712
        )
    )
    if watcher_user_id:
        from opentask.models.issue_watcher.model import IssueWatcher

        q = q.join(
            IssueWatcher,
            and_(
                IssueWatcher.issue_id == IssueTimeline.issue_id,
                IssueWatcher.user_id == str(watcher_user_id),
                IssueWatcher.workspace_id == workspace_id,
            ),
        )
    if issue_id:
        q = q.where(IssueTimeline.issue_id == issue_id)
    if since is not None:
        q = q.where(IssueTimeline.created_at >= since)
    if until is not None:
        q = q.where(IssueTimeline.created_at <= until)
    if types:
        q = q.where(IssueTimeline.action_type.in_(types))
    if actor_id:
        q = q.where(IssueTimeline.user_id == actor_id)
    if cursor is not None:
        c_at, c_id = cursor
        q = q.where(
            or_(
                IssueTimeline.created_at < c_at,
                and_(IssueTimeline.created_at == c_at, IssueTimeline.id < c_id),
            )
        )

    q = q.order_by(IssueTimeline.created_at.desc(), IssueTimeline.id.desc()).limit(limit)
    result = await db.execute(q)
    return list(result.scalars().all())


def serialize_activity_item(
    row: IssueTimeline,
    *,
    issue: Optional[Issue] = None,
    actor_user: Optional[UserModel] = None,
    reactions: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """CamelCase activity feed item (E47/E52)."""
    actor: dict[str, Any] | None = None
    if row.user_id:
        display = None
        username = None
        if actor_user is not None:
            display = (
                getattr(actor_user, "sso_name", None)
                or actor_user.name
                or getattr(actor_user, "username", None)
                or str(actor_user.id)
            )
            username = getattr(actor_user, "username", None) or actor_user.name
        actor = {
            "id": str(row.user_id),
            "username": username,
            "displayName": display,
        }
    out: dict[str, Any] = {
        "id": row.id,
        "issueId": row.issue_id,
        "issueCode": (issue.issue_code if issue is not None else None),
        "issueTitle": (issue.title if issue is not None else None),
        "actionType": _action_type_value(row.action_type),
        "actor": actor,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "payload": row.action_data or {},
    }
    if reactions is not None:
        out["reactions"] = reactions
    return out


def reactions_payload_for_row(
    row: IssueTimeline,
    *,
    issue_maps: dict[str, dict[str, list[str]]],
    comment_maps: dict[str, dict[str, list[str]]],
    viewer_id: str | None,
) -> dict[str, Any]:
    """Q2a: comment reactions when payload has comment_id; else issue-level."""
    payload = row.action_data or {}
    cid = extract_comment_id(payload)
    if cid:
        return {
            "scope": "comment",
            "commentId": cid,
            "summary": build_reaction_summary(comment_maps.get(cid, {}), viewer_id=viewer_id),
        }
    return {
        "scope": "issue",
        "summary": build_reaction_summary(issue_maps.get(row.issue_id, {}), viewer_id=viewer_id),
    }


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

    rows = await query_timeline_entries(
        db,
        workspace_id=workspace_id,
        issue_id=issue_id,
        since=since,
        action_types=action_types,
        limit=lim + 1,
    )
    truncated = len(rows) > lim
    rows = rows[:lim]

    user_ids = list({r.user_id for r in rows if r.user_id})
    name_map: dict[str, str] = {}
    if user_ids:
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
