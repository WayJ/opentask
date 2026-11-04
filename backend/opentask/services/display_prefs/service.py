"""Issue Display prefs 服务（E7-S3 + E37 CF 泳道）"""
from __future__ import annotations

import re
from copy import deepcopy
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.custom_field.model import CustomField
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
    "custom_field_keys": [],
    "conditional_formats": [],
}

_CFMT_TINTS = frozenset({"danger", "warning", "success", "info", "neutral"})
_CFMT_TARGETS = frozenset({"row", "cell"})
_CFMT_OPS = frozenset({"eq", "neq", "gt", "gte", "lt", "lte"})
_CFMT_SYSTEM_FIELDS = frozenset({"priority", "status", "due_date", "estimate_points"})
_CFMT_MAX = 10
_CFMT_FIELD_RE = re.compile(r"^(?:cf:([a-z][a-z0-9_-]{0,63})|priority|status|due_date|estimate_points)$")


_SWIMLANE_OK = {"none", "assignee", "priority", "type", "label"}
_VIEW_MODE_OK = {"list", "board"}
_GROUP_BY_OK = {"none", "status", "assignee", "priority", "type", "label"}

CF_GROUPING_TYPES = frozenset(
    {"single_select", "boolean", "text", "number", "date"}
)
_CF_DIM_RE = re.compile(r"^cf:([a-z][a-z0-9_-]{0,63})$")


def parse_cf_dim(value: Any) -> Optional[str]:
    """Return field key if value is well-formed cf:<slug>; else None."""
    if not isinstance(value, str):
        return None
    m = _CF_DIM_RE.match(value.strip())
    return m.group(1) if m else None


def _is_swimlane_value(value: Any) -> bool:
    if value in _SWIMLANE_OK:
        return True
    return parse_cf_dim(value) is not None


def _is_group_by_value(value: Any) -> bool:
    if value in _GROUP_BY_OK:
        return True
    return parse_cf_dim(value) is not None


def normalize_display_json(raw: Any) -> dict[str, Any]:
    """合并缺省；未知顶层键忽略；fields 内未知键忽略；接受系统枚举或 cf:<key> 形态。"""
    out = deepcopy(DEFAULT_DISPLAY)
    if not isinstance(raw, dict):
        return out

    vm = raw.get("view_mode")
    if vm in _VIEW_MODE_OK:
        out["view_mode"] = vm

    gb = raw.get("group_by")
    if _is_group_by_value(gb):
        out["group_by"] = gb
    # 畸形 cf: 或未知 → 保持默认 none

    sb = raw.get("swimlane_by")
    if _is_swimlane_value(sb):
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

    keys: list[str] = []
    seen: set[str] = set()
    cf_keys = raw.get("custom_field_keys")
    if isinstance(cf_keys, list):
        for k in cf_keys:
            kk = str(k or "").strip().lower()
            if not kk or kk in seen:
                continue
            seen.add(kk)
            keys.append(kk)
    out["custom_field_keys"] = keys
    out["conditional_formats"] = _normalize_conditional_formats(
        raw.get("conditional_formats") or raw.get("conditionalFormats")
    )
    return out


def _normalize_conditional_formats(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        when = item.get("when")
        style = item.get("style")
        if not isinstance(when, dict) or not isinstance(style, dict):
            continue
        field = str(when.get("field") or "").strip()
        if not _CFMT_FIELD_RE.match(field):
            continue
        op = str(when.get("op") or "").strip().lower()
        if op not in _CFMT_OPS:
            continue
        tint = str(style.get("rowTint") or style.get("row_tint") or "").strip().lower()
        if tint not in _CFMT_TINTS:
            continue
        target = str(item.get("target") or "row").strip().lower()
        if target not in _CFMT_TARGETS:
            continue
        cid = str(item.get("id") or "").strip() or f"cfmt_{len(out)+1}"
        out.append(
            {
                "id": cid,
                "when": {"field": field, "op": op, "value": when.get("value")},
                "style": {"rowTint": tint},
                "target": target,
            }
        )
        if len(out) >= _CFMT_MAX:
            break
    return out


def _merge_cf_key(display: dict[str, Any], key: str) -> None:
    keys = list(display.get("custom_field_keys") or [])
    if key not in keys:
        keys.append(key)
    display["custom_field_keys"] = keys


async def _lookup_grouping_field(
    db: AsyncSession, *, workspace_id: str, key: str
) -> Optional[CustomField]:
    result = await db.execute(
        select(CustomField).where(
            CustomField.workspace_id == workspace_id,
            CustomField.key == key,
        )
    )
    return result.scalar_one_or_none()


async def _resolve_cf_dim(
    db: AsyncSession,
    *,
    workspace_id: str,
    dim_value: str,
    on_write: bool,
) -> str:
    """Validate cf:<key>; return dim_value or 'none' (read) / raise 400 (write)."""
    key = parse_cf_dim(dim_value)
    if key is None:
        if on_write:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"非法分组维: {dim_value}",
            )
        return "none"

    field = await _lookup_grouping_field(db, workspace_id=workspace_id, key=key)
    if field is None or field.archived_at is not None:
        if on_write:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"自定义字段不可用于分组: {key}",
            )
        return "none"
    if field.type == "formula":
        rt = (field.formula_result_type or "number").strip() or "number"
        if rt not in {"number", "text", "boolean"}:
            if on_write:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"公式结果类型 {rt} 不支持作为泳道/分组",
                )
            return "none"
        return dim_value
    if field.type not in CF_GROUPING_TYPES:
        if on_write:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"字段类型 {field.type} 不支持作为泳道/分组",
            )
        return "none"
    return dim_value


async def validate_and_normalize_display(
    db: AsyncSession,
    *,
    workspace_id: str,
    raw: Any,
    on_write: bool,
) -> dict[str, Any]:
    """Shape-normalize then validate cf:* dims against workspace fields."""
    if on_write and isinstance(raw, dict):
        cfmt = raw.get("conditional_formats")
        if cfmt is None:
            cfmt = raw.get("conditionalFormats")
        if isinstance(cfmt, list) and len(cfmt) > _CFMT_MAX:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "conditional_formats_too_many",
                    "message": f"conditionalFormats 最多 {_CFMT_MAX} 条",
                },
            )
    out = normalize_display_json(raw)

    gb = out.get("group_by")
    if parse_cf_dim(gb) is not None:
        out["group_by"] = await _resolve_cf_dim(
            db, workspace_id=workspace_id, dim_value=str(gb), on_write=on_write
        )
        if parse_cf_dim(out["group_by"]):
            _merge_cf_key(out, parse_cf_dim(out["group_by"]) or "")

    sb = out.get("swimlane_by")
    if parse_cf_dim(sb) is not None:
        out["swimlane_by"] = await _resolve_cf_dim(
            db, workspace_id=workspace_id, dim_value=str(sb), on_write=on_write
        )
        if parse_cf_dim(out["swimlane_by"]):
            _merge_cf_key(out, parse_cf_dim(out["swimlane_by"]) or "")

    return out


def serialize_display_prefs_sync(row: Optional[IssueDisplayPrefs]) -> dict[str, Any]:
    """Legacy sync serialize (shape only). Prefer async serialize with validation."""
    if row is None:
        return {"display": None}
    return {"display": normalize_display_json(row.display_json)}


async def serialize_display_prefs(
    db: AsyncSession,
    *,
    workspace_id: str,
    row: Optional[IssueDisplayPrefs],
) -> dict[str, Any]:
    if row is None:
        return {"display": None}
    display = await validate_and_normalize_display(
        db, workspace_id=workspace_id, raw=row.display_json, on_write=False
    )
    return {"display": display}


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
        normalized = await validate_and_normalize_display(
            self.db, workspace_id=workspace_id, raw=display, on_write=True
        )
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
