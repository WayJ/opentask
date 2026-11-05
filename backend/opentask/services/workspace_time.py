"""E67: workspace timezone → local calendar day helpers."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from opentask.services.sla.business_hours import validate_timezone


def resolve_workspace_tz(ws: Any) -> ZoneInfo:
    """Return ZoneInfo for workspace timezone; None/empty/invalid → UTC (never raises)."""
    raw: Optional[str] = None
    if ws is None:
        raw = None
    elif isinstance(ws, str):
        raw = ws
    else:
        raw = getattr(ws, "timezone", None)
    try:
        name = validate_timezone(raw)
    except ValueError:
        return ZoneInfo("UTC")
    if not name:
        return ZoneInfo("UTC")
    return ZoneInfo(name)


def local_today(ws: Any, *, now_utc: datetime | None = None) -> date:
    """Calendar date in workspace TZ for the given UTC instant (naive treated as UTC)."""
    tz = resolve_workspace_tz(ws)
    now = now_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    else:
        now = now.astimezone(timezone.utc)
    return now.astimezone(tz).date()
