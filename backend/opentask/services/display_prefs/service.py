"""Issue Display prefs 服务（E7-S3）"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue_display_prefs.model import IssueDisplayPrefs

DEFAULT_FIELDS: dict[str, bool] = {
    "assignee": True,
    "priority": True,
    "labels": True,
    "estimate_points": True,
    "due_date": False,
    "project": False,
    "cycle": False,
    "issue_code": True,
    "type": False,
}

DEFAULT_DISPLAY: dict[str, Any] = {
    "view_mode": "list",
    "group_by": "none",
    "swimlane_by": "none",
    "hide_empty_lanes": False,
    "fields": dict(DEFAULT_FIELDS),
}

_SWIMLANE_OK = {"none", "assignee", "priority", "type", "label"}
_VIEW_MODE_OK = {"list", "board"}
_GROUP_BY_OK = {"none", "status", "assignee", "priority", "type", "label"}


def normalize_display_json(raw: Any) -> dict[str, Any]:
    """合并缺省；未知顶层键忽略；fields 内未知键忽略。"""
    out = deepcopy(DEFAULT_DISPLAY)
    if not isinstance(raw, dict):
        return out

    vm = raw.get("view_mode")
    if vm in _VIEW_MODE_OK:
        out["view_mode"] = vm

    gb = raw.get("group_by")
    if gb in _GROUP_BY_OK:
        out["group_by"] = gb

    sb = raw.get("swimlane_by")
    if sb in _SWIMLANE_OK:
        out["swimlane_by"] = sb

    if "hide_empty_lanes" in raw:
        out["hide_empty_lanes"] = bool(raw.get("hide_empty_lanes"))

    fields_in = raw.get("fields")
    if isinstance(fields_in, dict):
        fields = dict(DEFAULT_FIELDS)
        for key in DEFAULT_FIELDS:
            if key in fields_in:
                fields[key] = bool(fields_in[key])
        out["fields"] = fields

    return out


def serialize_display_prefs(row: Optional[IssueDisplayPrefs]) -> dict[str, Any]:
    if row is None:
        return {"display": None}
    return {"display": normalize_display_json(row.display_json)}


class DisplayPrefsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(
        self, *, workspace_id: str, user_id: str
    ) -> Optional[IssueDisplayPrefs]:
        q = await self.db.execute(
            select(IssueDisplayPrefs).where(
                IssueDisplayPrefs.workspace_id == workspace_id,
                IssueDisplayPrefs.user_id == str(user_id),
            )
        )
        return q.scalar_one_or_none()

    async def upsert(
        self, *, workspace_id: str, user_id: str, display: Any
    ) -> IssueDisplayPrefs:
        normalized = normalize_display_json(display)
        existing = await self.get(workspace_id=workspace_id, user_id=user_id)
        if existing is None:
            row = IssueDisplayPrefs(
                workspace_id=workspace_id,
                user_id=str(user_id),
                display_json=normalized,
            )
            self.db.add(row)
            await self.db.commit()
            await self.db.refresh(row)
            return row

        existing.display_json = normalized
        existing.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(existing)
        return existing
