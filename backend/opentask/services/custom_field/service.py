"""Custom field definitions + issue values (E25)."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.custom_field.model import (
    FIELD_TYPES,
    CustomField,
    IssueCustomFieldValue,
)
from opentask.models.workspace.model import WorkspaceMember

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


def slugify_key(raw: str) -> str:
    s = (raw or "").strip().lower()
    s = re.sub(r"[^a-z0-9_-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_-")
    if not s:
        s = "field"
    if s[0].isdigit() or s[0] in "_-":
        s = "f_" + s
    return s[:64]


def normalize_options(options: list[Any] | None, field_type: str) -> list[dict]:
    if field_type not in ("single_select", "multi_select"):
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for item in options or []:
        if isinstance(item, str):
            value = item.strip()
            label = value
        elif isinstance(item, dict):
            value = str(item.get("value") or item.get("id") or "").strip()
            label = str(item.get("label") or value).strip()
        else:
            continue
        if not value or value in seen:
            continue
        seen.add(value)
        out.append({"value": value, "label": label or value})
    return out


def validate_value(field: CustomField, value: Any) -> Any:
    """Normalize + validate value_json for field.type. None means clear."""
    if value is None:
        return None
    t = field.type
    if t == "text":
        if not isinstance(value, str):
            raise HTTPException(status_code=400, detail=f"字段 {field.key} 需要 text")
        return value
    if t == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise HTTPException(status_code=400, detail=f"字段 {field.key} 需要 number")
        return value
    if t == "boolean":
        if not isinstance(value, bool):
            raise HTTPException(status_code=400, detail=f"字段 {field.key} 需要 boolean")
        return value
    if t == "date":
        if not isinstance(value, str) or not _DATE_RE.match(value):
            raise HTTPException(
                status_code=400, detail=f"字段 {field.key} 需要 YYYY-MM-DD"
            )
        return value
    opts = {o["value"] for o in (field.options_json or []) if isinstance(o, dict)}
    if t == "single_select":
        if not isinstance(value, str) or value not in opts:
            raise HTTPException(
                status_code=400, detail=f"字段 {field.key} 取值不在 options 内"
            )
        return value
    if t == "multi_select":
        if not isinstance(value, list) or any(not isinstance(x, str) for x in value):
            raise HTTPException(
                status_code=400, detail=f"字段 {field.key} 需要 string 数组"
            )
        bad = [x for x in value if x not in opts]
        if bad:
            raise HTTPException(
                status_code=400, detail=f"字段 {field.key} 含非法选项: {bad}"
            )
        # dedupe preserve order
        seen: set[str] = set()
        out: list[str] = []
        for x in value:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out
    raise HTTPException(status_code=400, detail=f"未知字段类型: {t}")


def serialize_field(row: CustomField) -> dict:
    return {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "name": row.name,
        "key": row.key,
        "type": row.type,
        "options": list(row.options_json or []),
        "position": row.position,
        "archivedAt": row.archived_at.isoformat() if row.archived_at else None,
        "createdBy": row.created_by,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def serialize_issue_field(
    field: CustomField, value: Any | None, *, include_options: bool = True
) -> dict:
    data = {
        "fieldId": field.id,
        "key": field.key,
        "name": field.name,
        "type": field.type,
        "value": value,
        "archived": field.archived_at is not None,
    }
    if include_options and field.type in ("single_select", "multi_select"):
        data["options"] = list(field.options_json or [])
    return data


class CustomFieldService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, *, workspace_id: str, field_id: str) -> CustomField:
        result = await self.db.execute(
            select(CustomField).where(
                CustomField.id == field_id,
                CustomField.workspace_id == workspace_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND, detail="自定义字段不存在"
            )
        return row

    async def get_by_key(self, *, workspace_id: str, key: str) -> CustomField:
        result = await self.db.execute(
            select(CustomField).where(
                CustomField.workspace_id == workspace_id,
                CustomField.key == key,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND, detail="自定义字段不存在"
            )
        return row

    async def list(
        self, *, workspace_id: str, include_archived: bool = False
    ) -> list[CustomField]:
        q = select(CustomField).where(CustomField.workspace_id == workspace_id)
        if not include_archived:
            q = q.where(CustomField.archived_at.is_(None))
        q = q.order_by(CustomField.position.asc(), CustomField.created_at.asc())
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def _next_position(self, workspace_id: str) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.max(CustomField.position), -1)).where(
                CustomField.workspace_id == workspace_id
            )
        )
        return int(result.scalar_one()) + 1

    async def create(
        self,
        *,
        workspace_id: str,
        user_id: str,
        name: str,
        field_type: str,
        key: str | None = None,
        options: list[Any] | None = None,
        position: int | None = None,
    ) -> CustomField:
        if field_type not in FIELD_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"type 必须是 {', '.join(FIELD_TYPES)}",
            )
        name = name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="name 不能为空")
        raw_key = key.strip() if key else slugify_key(name)
        raw_key = slugify_key(raw_key) if key else raw_key
        if not _SLUG_RE.match(raw_key):
            raise HTTPException(
                status_code=400,
                detail="key 须匹配 ^[a-z][a-z0-9_-]{0,63}$",
            )
        opts = normalize_options(options, field_type)
        if field_type in ("single_select", "multi_select") and not opts:
            raise HTTPException(status_code=400, detail="select 类型需要 options")
        pos = position if position is not None else await self._next_position(workspace_id)
        row = CustomField(
            workspace_id=workspace_id,
            name=name,
            key=raw_key,
            type=field_type,
            options_json=opts,
            position=pos,
            created_by=user_id,
        )
        self.db.add(row)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="同 key 字段已存在",
            )
        await self.db.refresh(row)
        return row

    async def update(
        self,
        *,
        workspace_id: str,
        field_id: str,
        name: str | None = None,
        options: list[Any] | None = None,
        set_options: bool = False,
        position: int | None = None,
        archive: bool | None = None,
    ) -> CustomField:
        row = await self.get(workspace_id=workspace_id, field_id=field_id)
        # type/key 不可变（避免历史值语义漂移）
        if name is not None:
            name = name.strip()
            if not name:
                raise HTTPException(status_code=400, detail="name 不能为空")
            row.name = name
        if set_options:
            if row.type not in ("single_select", "multi_select"):
                raise HTTPException(status_code=400, detail="仅 select 可改 options")
            opts = normalize_options(options, row.type)
            if not opts:
                raise HTTPException(status_code=400, detail="select 类型需要 options")
            row.options_json = opts
        if position is not None:
            row.position = position
        if archive is True:
            row.archived_at = datetime.utcnow()
        elif archive is False:
            row.archived_at = None
        row.updated_at = datetime.utcnow()
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT, detail="更新冲突"
            )
        await self.db.refresh(row)
        return row

    async def _value_count(self, field_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(IssueCustomFieldValue)
            .where(IssueCustomFieldValue.field_id == field_id)
        )
        return int(result.scalar_one())

    async def delete(self, *, workspace_id: str, field_id: str) -> None:
        row = await self.get(workspace_id=workspace_id, field_id=field_id)
        count = await self._value_count(field_id)
        if count > 0:
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="字段已有取值，请先归档（archive）",
            )
        await self.db.delete(row)
        await self.db.commit()

    async def reorder(
        self, *, workspace_id: str, ordered_ids: list[str]
    ) -> list[CustomField]:
        rows = await self.list(workspace_id=workspace_id, include_archived=True)
        by_id = {r.id: r for r in rows}
        for idx, fid in enumerate(ordered_ids):
            if fid in by_id:
                by_id[fid].position = idx
                by_id[fid].updated_at = datetime.utcnow()
        await self.db.commit()
        return await self.list(workspace_id=workspace_id, include_archived=False)

    # ---- issue values ----

    async def values_for_issues(
        self, *, workspace_id: str, issue_ids: list[str]
    ) -> dict[str, list[dict]]:
        if not issue_ids:
            return {}
        fields = await self.list(workspace_id=workspace_id, include_archived=True)
        if not fields:
            return {iid: [] for iid in issue_ids}
        field_by_id = {f.id: f for f in fields}
        result = await self.db.execute(
            select(IssueCustomFieldValue).where(
                IssueCustomFieldValue.issue_id.in_(issue_ids),
                IssueCustomFieldValue.field_id.in_(list(field_by_id.keys())),
            )
        )
        value_rows = list(result.scalars().all())
        by_issue: dict[str, dict[str, Any]] = {iid: {} for iid in issue_ids}
        for vr in value_rows:
            by_issue.setdefault(vr.issue_id, {})[vr.field_id] = vr.value_json

        # Active fields first by position; then archived that have a value
        active = [f for f in fields if f.archived_at is None]
        out: dict[str, list[dict]] = {}
        for iid in issue_ids:
            items: list[dict] = []
            seen_ids: set[str] = set()
            for f in active:
                items.append(
                    serialize_issue_field(f, by_issue.get(iid, {}).get(f.id))
                )
                seen_ids.add(f.id)
            for f in fields:
                if f.id in seen_ids:
                    continue
                if f.id in by_issue.get(iid, {}):
                    items.append(
                        serialize_issue_field(f, by_issue[iid][f.id])
                    )
            out[iid] = items
        return out

    async def upsert_issue_values(
        self,
        *,
        workspace_id: str,
        issue_id: str,
        entries: list[dict],
    ) -> list[dict]:
        """entries: [{fieldId?, key?, value}] ; value null clears."""
        if not entries:
            return (await self.values_for_issues(
                workspace_id=workspace_id, issue_ids=[issue_id]
            )).get(issue_id, [])

        for entry in entries:
            field_id = entry.get("fieldId") or entry.get("field_id")
            key = entry.get("key")
            if field_id:
                field = await self.get(workspace_id=workspace_id, field_id=str(field_id))
            elif key:
                field = await self.get_by_key(workspace_id=workspace_id, key=str(key))
            else:
                raise HTTPException(status_code=400, detail="需要 fieldId 或 key")
            if field.archived_at is not None:
                raise HTTPException(
                    status_code=400, detail=f"字段 {field.key} 已归档，不可写入"
                )
            raw_value = entry.get("value", entry.get("value_json"))
            # Allow explicit clear via null / missing with clear=True
            if "value" not in entry and "value_json" not in entry and entry.get("clear"):
                raw_value = None
            normalized = validate_value(field, raw_value)

            result = await self.db.execute(
                select(IssueCustomFieldValue).where(
                    IssueCustomFieldValue.issue_id == issue_id,
                    IssueCustomFieldValue.field_id == field.id,
                )
            )
            row = result.scalar_one_or_none()
            if normalized is None:
                if row:
                    await self.db.delete(row)
                continue
            if row is None:
                row = IssueCustomFieldValue(
                    issue_id=issue_id,
                    field_id=field.id,
                    value_json=normalized,
                )
                self.db.add(row)
            else:
                row.value_json = normalized
                row.updated_at = datetime.utcnow()

        await self.db.commit()
        return (await self.values_for_issues(
            workspace_id=workspace_id, issue_ids=[issue_id]
        )).get(issue_id, [])

    async def get_by_key_optional(
        self, *, workspace_id: str, key: str
    ) -> CustomField | None:
        result = await self.db.execute(
            select(CustomField).where(
                CustomField.workspace_id == workspace_id,
                CustomField.key == key,
            )
        )
        return result.scalar_one_or_none()

    async def apply_list_filters(self, query, *, workspace_id: str, filters: list[tuple[str, str]]):
        """AND-combine custom field filters onto an Issue select. Unknown key → empty."""
        from opentask.models.issue.model import Issue

        if not filters:
            return query
        for key, raw in filters:
            field = await self.get_by_key_optional(workspace_id=workspace_id, key=key)
            if field is None:
                return query.where(Issue.id.in_([]))
            expected = coerce_cf_filter_value(field, raw)
            if expected is None:
                return query.where(Issue.id.in_([]))
            match = cf_value_match_clause(field, expected)
            subq = (
                select(IssueCustomFieldValue.issue_id)
                .where(
                    IssueCustomFieldValue.field_id == field.id,
                    match,
                )
            )
            query = query.where(Issue.id.in_(subq))
        return query


# ---------------------------------------------------------------------------
# E32 · list / SmartSearch filters
# ---------------------------------------------------------------------------

_CF_BOOL_TRUE = {"true", "1", "yes", "y", "on"}
_CF_BOOL_FALSE = {"false", "0", "no", "n", "off"}


def parse_cf_query_items(query_items: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Parse request query into [(field_key, raw_value), ...].

    Accepts:
      - cf.<key>=value
      - cf=key=value  (first '=' splits)
    """
    out: list[tuple[str, str]] = []
    for name, value in query_items:
        if name.startswith("cf.") and len(name) > 3:
            key = name[3:].strip().lower()
            if key:
                out.append((key, value))
            continue
        if name == "cf":
            raw = value or ""
            if "=" not in raw:
                continue
            key, _, rest = raw.partition("=")
            key = key.strip().lower()
            if key:
                out.append((key, rest))
    return out


def coerce_cf_filter_value(field: CustomField, raw: str) -> Any | None:
    """Coerce query string to comparable JSON value. None = invalid → empty match."""
    t = field.type
    s = (raw if raw is not None else "").strip()
    if t == "text":
        return s
    if t == "number":
        try:
            if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
                return int(s)
            return float(s)
        except ValueError:
            return None
    if t == "boolean":
        low = s.lower()
        if low in _CF_BOOL_TRUE:
            return True
        if low in _CF_BOOL_FALSE:
            return False
        return None
    if t == "date":
        if not _DATE_RE.match(s):
            return None
        return s
    if t in ("single_select", "multi_select"):
        return s
    return None


def cf_value_match_clause(field: CustomField, expected: Any):
    """SQLAlchemy WHERE fragment for IssueCustomFieldValue.value_json."""
    import json
    from sqlalchemy import cast, literal
    from sqlalchemy.dialects.postgresql import JSONB

    col = cast(IssueCustomFieldValue.value_json, JSONB)
    rhs = cast(literal(json.dumps(expected if field.type != "multi_select" else [expected])), JSONB)
    if field.type == "multi_select":
        return col.op("@>")(rhs)
    return col == rhs
