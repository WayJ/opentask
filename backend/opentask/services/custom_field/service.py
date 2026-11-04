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
    IssueFormulaCache,
)
from opentask.models.workspace.model import WorkspaceMember
from opentask.services.custom_field.formula import (
    MAX_FORMULA_DEPTH,
    RESULT_TYPES,
    FormulaError,
    days_until_due_value,
    eval_parsed,
    issue_field_value,
    parse_formula,
)

_SLUG_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

FORMULA_FILTER_CANDIDATE_CAP = 2000
FORMULA_SORT_CANDIDATE_CAP = FORMULA_FILTER_CANDIDATE_CAP

CF_FILTER_OPS = frozenset({"eq", "gt", "gte", "lt", "lte"})
CF_RANGE_OPS = frozenset({"gt", "gte", "lt", "lte"})
_CF_KEY_OP_RE = re.compile(
    r"^([a-z][a-z0-9_-]{0,63})(?:\[(eq|gt|gte|lt|lte)\])?$"
)


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
    if field.type == "formula":
        raise HTTPException(status_code=400, detail="公式字段只读")
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
    is_formula = row.type == "formula"
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
        "formulaExpr": row.formula_expr if is_formula else None,
        "formulaResultType": row.formula_result_type if is_formula else None,
    }


def serialize_issue_field(
    field: CustomField,
    value: Any | None,
    *,
    include_options: bool = True,
    computed: bool | None = None,
    error: str | None = None,
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
    if computed is not None:
        data["computed"] = computed
    elif field.type == "formula":
        data["computed"] = True
    if error:
        data["error"] = error
    if field.type == "formula":
        data["formulaResultType"] = field.formula_result_type or "number"
    return data



def _truncate_timeline_value(value, max_bytes: int = 2048):
    """JSON-able value truncated to ~max_bytes UTF-8 for timeline action_data."""
    import json as _json

    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        raw = value.encode("utf-8")
        if len(raw) <= max_bytes:
            return value
        return raw[:max_bytes].decode("utf-8", errors="ignore") + "…"
    try:
        s = _json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except TypeError:
        s = str(value)
    raw = s.encode("utf-8")
    if len(raw) <= max_bytes:
        return value
    return raw[:max_bytes].decode("utf-8", errors="ignore") + "…"


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
        formula_expr: str | None = None,
        formula_result_type: str | None = None,
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
        f_expr, f_rtype = await self._normalize_formula_payload(
            workspace_id=workspace_id,
            field_type=field_type,
            formula_expr=formula_expr,
            formula_result_type=formula_result_type,
            self_key=raw_key,
            self_id=None,
        )
        opts = normalize_options(options, field_type)
        if field_type == "formula":
            opts = []
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
            formula_expr=f_expr,
            formula_result_type=f_rtype,
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
        formula_expr: str | None = None,
        formula_result_type: str | None = None,
        set_formula: bool = False,
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
        if set_formula or formula_expr is not None or formula_result_type is not None:
            if row.type != "formula":
                raise HTTPException(status_code=400, detail="仅 formula 可改表达式")
            new_expr = formula_expr if formula_expr is not None else row.formula_expr
            new_rt = (
                formula_result_type
                if formula_result_type is not None
                else (row.formula_result_type or "number")
            )
            f_expr, f_rtype = await self._normalize_formula_payload(
                workspace_id=workspace_id,
                field_type="formula",
                formula_expr=new_expr,
                formula_result_type=new_rt,
                self_key=row.key,
                self_id=row.id,
            )
            row.formula_expr = f_expr
            row.formula_result_type = f_rtype
            row.options_json = []
        if position is not None:
            row.position = position
        if archive is True:
            row.archived_at = datetime.utcnow()
        elif archive is False:
            row.archived_at = None
        row.updated_at = datetime.utcnow()
        formula_def_changed = bool(
            set_formula or formula_expr is not None or formula_result_type is not None
        ) and row.type == "formula"
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT, detail="更新冲突"
            )
        await self.db.refresh(row)
        if formula_def_changed:
            await self.invalidate_formula_cache(
                workspace_id=workspace_id, field_id=row.id
            )
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

    async def _normalize_formula_payload(
        self,
        *,
        workspace_id: str,
        field_type: str,
        formula_expr: str | None,
        formula_result_type: str | None,
        self_key: str,
        self_id: str | None,
    ) -> tuple[str | None, str | None]:
        """Validate formula fields for create/update. Returns (expr, result_type)."""
        if field_type != "formula":
            if formula_expr is not None or formula_result_type is not None:
                raise HTTPException(
                    status_code=400, detail="非 formula 类型禁止带 formulaExpr"
                )
            return None, None
        if formula_expr is None or not str(formula_expr).strip():
            raise HTTPException(status_code=400, detail="formula 需要 formulaExpr")
        expr = str(formula_expr).strip()
        rtype = (formula_result_type or "number").strip()
        if rtype not in RESULT_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"formulaResultType 必须是 {', '.join(RESULT_TYPES)}",
            )
        try:
            parsed = parse_formula(expr)
        except FormulaError as e:
            raise HTTPException(status_code=400, detail=f"公式无效: {e}") from e
        await self._assert_formula_deps_and_dag(
            workspace_id=workspace_id,
            cf_keys=parsed.cf_keys,
            self_key=self_key,
            self_id=self_id,
            self_expr_deps=parsed.cf_keys,
        )
        return expr, rtype

    async def _assert_formula_deps_and_dag(
        self,
        *,
        workspace_id: str,
        cf_keys: list[str],
        self_key: str,
        self_id: str | None,
        self_expr_deps: list[str],
    ) -> None:
        fields = await self.list(workspace_id=workspace_id, include_archived=True)
        by_key = {f.key: f for f in fields}
        for key in cf_keys:
            dep = by_key.get(key)
            if dep is None:
                raise HTTPException(
                    status_code=400, detail=f"依赖字段不存在: cf.{key}"
                )
            if dep.archived_at is not None:
                raise HTTPException(
                    status_code=400, detail=f"依赖字段已归档: cf.{key}"
                )
            if self_id and dep.id == self_id:
                raise HTTPException(status_code=400, detail="公式不能依赖自身")

        graph: dict[str, list[str]] = {}
        for f in fields:
            if f.type != "formula":
                continue
            if self_id and f.id == self_id:
                continue
            try:
                parsed = parse_formula(f.formula_expr or "")
            except FormulaError:
                continue
            graph[f.key] = [
                k for k in parsed.cf_keys if by_key.get(k) and by_key[k].type == "formula"
            ]
        graph[self_key] = [
            k
            for k in self_expr_deps
            if (k == self_key)
            or (by_key.get(k) and by_key[k].type == "formula")
        ]

        WHITE, GRAY, BLACK = 0, 1, 2
        color = {k: WHITE for k in graph}

        def dfs(node: str) -> None:
            color[node] = GRAY
            for nxt in graph.get(node, []):
                if nxt not in color:
                    color[nxt] = WHITE
                c = color.get(nxt, WHITE)
                if c == GRAY:
                    raise HTTPException(status_code=400, detail="公式存在循环依赖")
                if c == WHITE:
                    dfs(nxt)
            color[node] = BLACK

        for k in list(graph.keys()):
            if color.get(k, WHITE) == WHITE:
                dfs(k)

        memo: dict[str, int] = {}

        def depth_of(node: str, stack: set[str]) -> int:
            if node in memo:
                return memo[node]
            if node in stack:
                raise HTTPException(status_code=400, detail="公式存在循环依赖")
            stack.add(node)
            deps = graph.get(node, [])
            if not deps:
                d = 0
            else:
                d = 1 + max(depth_of(x, stack) for x in deps)
            stack.remove(node)
            memo[node] = d
            return d

        d = depth_of(self_key, set())
        if d > MAX_FORMULA_DEPTH:
            raise HTTPException(
                status_code=400,
                detail=f"公式依赖深度超过 {MAX_FORMULA_DEPTH}",
            )

    async def validate_formula_expr(
        self,
        *,
        workspace_id: str,
        formula_expr: str,
        formula_result_type: str | None = None,
    ) -> dict:
        try:
            parsed = parse_formula(formula_expr or "")
        except FormulaError as e:
            return {"ok": False, "dependencies": [], "error": str(e) or e.code}
        rtype = (formula_result_type or "number").strip()
        if formula_result_type is not None and rtype not in RESULT_TYPES:
            return {
                "ok": False,
                "dependencies": parsed.dependencies,
                "error": f"formulaResultType 必须是 {', '.join(RESULT_TYPES)}",
            }
        fields = await self.list(workspace_id=workspace_id, include_archived=False)
        by_key = {f.key: f for f in fields}
        for key in parsed.cf_keys:
            dep = by_key.get(key)
            if dep is None:
                return {
                    "ok": False,
                    "dependencies": parsed.dependencies,
                    "error": f"依赖字段不存在: cf.{key}",
                }
            if dep.archived_at is not None:
                return {
                    "ok": False,
                    "dependencies": parsed.dependencies,
                    "error": f"依赖字段已归档: cf.{key}",
                }
        return {"ok": True, "dependencies": parsed.dependencies}


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
        field_by_key = {f.key: f for f in fields}
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

        has_formula = any(f.type == "formula" and f.archived_at is None for f in fields)
        issues_by_id: dict[str, Any] = {}
        if has_formula:
            from opentask.models.issue.model import Issue

            ires = await self.db.execute(
                select(Issue).where(
                    Issue.id.in_(issue_ids),
                    Issue.workspace_id == workspace_id,
                )
            )
            for iss in ires.scalars().all():
                issues_by_id[iss.id] = iss

        active = [f for f in fields if f.archived_at is None]
        out: dict[str, list[dict]] = {}
        for iid in issue_ids:
            stored = by_issue.get(iid, {})
            cache: dict[str, tuple[Any, str | None]] = {}
            stack: set[str] = set()

            def eval_one(field: CustomField) -> tuple[Any, str | None]:
                if field.id in cache:
                    return cache[field.id]
                if field.type != "formula":
                    return stored.get(field.id), None
                if field.id in stack:
                    cache[field.id] = (None, "dep_error")
                    return cache[field.id]
                stack.add(field.id)
                issue = issues_by_id.get(iid)
                if issue is None:
                    cache[field.id] = (None, "dep_error")
                    stack.discard(field.id)
                    return cache[field.id]
                try:
                    parsed = parse_formula(field.formula_expr or "")
                except FormulaError:
                    cache[field.id] = (None, "parse_error")
                    stack.discard(field.id)
                    return cache[field.id]

                def cf_get(key: str) -> Any:
                    dep = field_by_key.get(key)
                    if dep is None or dep.archived_at is not None:
                        raise FormulaError("dep_error")
                    if dep.type == "formula":
                        val, err = eval_one(dep)
                        if err:
                            raise FormulaError("dep_error")
                        return val
                    return stored.get(dep.id)

                def issue_get(name: str) -> Any:
                    return issue_field_value(issue, name)

                value, err = eval_parsed(
                    parsed,
                    cf_get=cf_get,
                    issue_get=issue_get,
                    days_until_due=days_until_due_value(issue),
                    result_type=field.formula_result_type or "number",
                )
                cache[field.id] = (value, err)
                stack.discard(field.id)
                return cache[field.id]

            items: list[dict] = []
            seen_ids: set[str] = set()
            for f in active:
                if f.type == "formula":
                    val, err = eval_one(f)
                    items.append(
                        serialize_issue_field(
                            f, val, computed=True, error=err
                        )
                    )
                else:
                    items.append(serialize_issue_field(f, stored.get(f.id)))
                seen_ids.add(f.id)
            for f in fields:
                if f.id in seen_ids:
                    continue
                if f.id in stored:
                    items.append(serialize_issue_field(f, stored[f.id]))
            out[iid] = items
        return out

    async def upsert_issue_values(
        self,
        *,
        workspace_id: str,
        issue_id: str,
        entries: list[dict],
        actor_user_id: Optional[str] = None,
    ) -> list[dict]:
        """entries: [{fieldId?, key?, value}] ; value null clears.

        E36: after commit, emit custom_field_changed per actually-changed field
        (best-effort; respects automation depth anti-loop).
        """
        if not entries:
            return (await self.values_for_issues(
                workspace_id=workspace_id, issue_ids=[issue_id]
            )).get(issue_id, [])

        changes: list[dict[str, Any]] = []

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
            if field.type == "formula":
                raise HTTPException(status_code=400, detail="公式字段只读")
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
            old_value = row.value_json if row is not None else None

            if normalized is None:
                if row:
                    await self.db.delete(row)
                    if old_value is not None:
                        changes.append(
                            {
                                "field_id": field.id,
                                "field_key": field.key,
                                "from": old_value,
                                "to": None,
                            }
                        )
                continue
            if row is None:
                row = IssueCustomFieldValue(
                    issue_id=issue_id,
                    field_id=field.id,
                    value_json=normalized,
                )
                self.db.add(row)
                changes.append(
                    {
                        "field_id": field.id,
                        "field_key": field.key,
                        "from": None,
                        "to": normalized,
                    }
                )
            else:
                if old_value == normalized:
                    continue
                row.value_json = normalized
                row.updated_at = datetime.utcnow()
                changes.append(
                    {
                        "field_id": field.id,
                        "field_key": field.key,
                        "from": old_value,
                        "to": normalized,
                    }
                )

        # E41：同事务写入 custom_field_changed timeline（每字段一条）
        if changes:
            from opentask.models.issue.enums import TimelineAction
            from opentask.models.issue.model import IssueTimeline

            for ch in changes:
                self.db.add(
                    IssueTimeline(
                        issue_id=issue_id,
                        user_id=actor_user_id,
                        action_type=TimelineAction.CUSTOM_FIELD_CHANGED,
                        action_data={
                            "fieldId": ch["field_id"],
                            "fieldKey": ch["field_key"],
                            "from": _truncate_timeline_value(ch["from"]),
                            "to": _truncate_timeline_value(ch["to"]),
                        },
                    )
                )

        await self.db.commit()

        if changes:
            await self._emit_custom_field_changed(
                workspace_id=workspace_id,
                issue_id=issue_id,
                changes=changes,
                actor_user_id=actor_user_id,
            )
            # E43: best-effort refresh formulas depending on changed CF keys (NEVER emit)
            try:
                changed_keys = [c["field_key"] for c in changes]
                await self.refresh_formula_cache_for_issue(
                    workspace_id=workspace_id,
                    issue_id=issue_id,
                    depending_on_cf_keys=changed_keys,
                )
            except Exception:
                import logging

                logging.getLogger(__name__).exception(
                    "formula cache refresh failed issue=%s", issue_id
                )

        return (await self.values_for_issues(
            workspace_id=workspace_id, issue_ids=[issue_id]
        )).get(issue_id, [])

    async def _emit_custom_field_changed(
        self,
        *,
        workspace_id: str,
        issue_id: str,
        changes: list[dict[str, Any]],
        actor_user_id: Optional[str] = None,
    ) -> None:
        """Best-effort E36 emit; never raises to caller."""
        try:
            from opentask.models.issue.model import Issue
            from opentask.services.automation.service import fire_automations

            issue = await self.db.get(Issue, issue_id)
            if issue is None or getattr(issue, "is_deleted", False):
                return
            if issue.workspace_id != workspace_id:
                return
            from opentask.services.workspace_webhook.service import fire_webhooks

            for ch in changes:
                await fire_automations(
                    self.db,
                    workspace_id=workspace_id,
                    trigger_type="custom_field_changed",
                    issue=issue,
                    actor_user_id=actor_user_id,
                    event={
                        "issue_id": issue_id,
                        "field_key": ch["field_key"],
                        "field_id": ch["field_id"],
                        "from": ch["from"],
                        "to": ch["to"],
                        "old_value": ch["from"],
                        "new_value": ch["to"],
                        "workspace_id": workspace_id,
                    },
                )
                await fire_webhooks(
                    self.db,
                    workspace_id=workspace_id,
                    event_type="issue.custom_field_changed",
                    data={
                        "id": issue_id,
                        "issueCode": getattr(issue, "issue_code", None),
                        "title": issue.title,
                        "fieldId": ch["field_id"],
                        "fieldKey": ch["field_key"],
                        "from": ch["from"],
                        "to": ch["to"],
                        "actorUserId": actor_user_id,
                    },
                )
                # refresh in case prior rule mutated
                issue = await self.db.get(Issue, issue_id)
                if issue is None:
                    return
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "custom_field_changed emit failed issue=%s", issue_id
            )

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

    async def apply_list_filters(
        self, query, *, workspace_id: str, filters: list[tuple[str, str, str]]
    ):
        """AND-combine custom field filters onto an Issue select. Unknown key → empty.

        E43/E46: formula keys do NOT use IssueCustomFieldValue SQL — batch-eval (or cache)
        after non-formula filters, with FORMULA_FILTER_CANDIDATE_CAP.
        filters items are (key, op, raw) with op in {eq,gt,gte,lt,lte}.
        """
        from opentask.models.issue.model import Issue

        if not filters:
            return query

        stored_filters: list[tuple[CustomField, str, Any]] = []
        formula_filters: list[tuple[CustomField, str, Any]] = []
        for key, op, raw in filters:
            op = (op or "eq").lower()
            if op not in CF_FILTER_OPS:
                return query.where(Issue.id.in_([]))
            field = await self.get_by_key_optional(workspace_id=workspace_id, key=key)
            if field is None:
                return query.where(Issue.id.in_([]))
            if field.type == "formula" and field.archived_at is not None:
                return query.where(Issue.id.in_([]))
            if op in CF_RANGE_OPS and not _cf_range_type_ok(field):
                raise HTTPException(
                    status_code=400,
                    detail={
                        "code": "cf_range_unsupported",
                        "message": f"字段 {key} 不支持 range 过滤（仅 number/date）",
                    },
                )
            expected = coerce_cf_filter_value(field, raw)
            if expected is None:
                return query.where(Issue.id.in_([]))
            if field.type == "formula":
                formula_filters.append((field, op, expected))
            else:
                stored_filters.append((field, op, expected))

        for field, op, expected in stored_filters:
            if op == "eq":
                match = cf_value_match_clause(field, expected)
            else:
                match = cf_value_range_clause(field, op, expected)
            subq = (
                select(IssueCustomFieldValue.issue_id)
                .where(
                    IssueCustomFieldValue.field_id == field.id,
                    match,
                )
            )
            query = query.where(Issue.id.in_(subq))

        for field, op, expected in formula_filters:
            query = await self._apply_formula_list_filter(
                query,
                workspace_id=workspace_id,
                field=field,
                expected=expected,
                op=op,
            )
        return query

    async def _apply_formula_list_filter(
        self,
        query,
        *,
        workspace_id: str,
        field: CustomField,
        expected: Any,
        op: str = "eq",
    ):
        from opentask.models.issue.model import Issue

        # Count candidates under current query (other filters already applied)
        count_q = select(func.count()).select_from(
            query.order_by(None).with_only_columns(Issue.id).distinct().subquery()
        )
        n = await self.db.scalar(count_q)
        if n is None:
            n = 0
        if n > FORMULA_FILTER_CANDIDATE_CAP:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "formula_filter_too_broad",
                    "message": (
                        f"公式过滤候选超过 {FORMULA_FILTER_CANDIDATE_CAP}，"
                        "请先用 status/assignee/project 等条件收窄"
                    ),
                },
            )

        id_rows = await self.db.execute(
            query.order_by(None).with_only_columns(Issue.id).distinct()
        )
        candidate_ids = [row[0] for row in id_rows.all()]
        if not candidate_ids:
            return query.where(Issue.id.in_([]))

        matched = await self._match_formula_candidates(
            workspace_id=workspace_id,
            field=field,
            expected=expected,
            candidate_ids=candidate_ids,
            op=op,
        )
        return query.where(Issue.id.in_(matched or []))

    async def _match_formula_candidates(
        self,
        *,
        workspace_id: str,
        field: CustomField,
        expected: Any,
        candidate_ids: list[str],
        op: str = "eq",
    ) -> list[str]:
        """Op match via cache when ok; miss/error → batch eval + backfill."""
        cache_map = await self._load_formula_cache_map(
            workspace_id=workspace_id,
            field_id=field.id,
            issue_ids=candidate_ids,
        )
        matched: list[str] = []
        miss_ids: list[str] = []
        for iid in candidate_ids:
            row = cache_map.get(iid)
            if row is not None and row.error is None:
                val = row.value_json
                if val is None:
                    continue
                if _formula_values_compare(
                    val, op, expected, field.formula_result_type or "number"
                ):
                    matched.append(iid)
            else:
                miss_ids.append(iid)

        if miss_ids:
            bundled = await self.values_for_issues(
                workspace_id=workspace_id, issue_ids=miss_ids
            )
            # backfill cache (best-effort; never emit)
            try:
                await self._upsert_formula_cache_from_bundled(
                    workspace_id=workspace_id,
                    field=field,
                    bundled=bundled,
                    issue_ids=miss_ids,
                )
            except Exception:
                import logging

                logging.getLogger(__name__).exception(
                    "formula cache backfill failed field=%s", field.id
                )
            for iid in miss_ids:
                items = bundled.get(iid) or []
                entry = next((x for x in items if x.get("key") == field.key), None)
                if not entry or entry.get("error"):
                    continue
                val = entry.get("value")
                if val is None:
                    continue
                if _formula_values_compare(
                    val, op, expected, field.formula_result_type or "number"
                ):
                    matched.append(iid)
        return matched

    async def _load_formula_cache_map(
        self, *, workspace_id: str, field_id: str, issue_ids: list[str]
    ) -> dict[str, IssueFormulaCache]:
        if not issue_ids:
            return {}
        result = await self.db.execute(
            select(IssueFormulaCache).where(
                IssueFormulaCache.workspace_id == workspace_id,
                IssueFormulaCache.field_id == field_id,
                IssueFormulaCache.issue_id.in_(issue_ids),
            )
        )
        return {r.issue_id: r for r in result.scalars().all()}

    async def _upsert_formula_cache_from_bundled(
        self,
        *,
        workspace_id: str,
        field: CustomField,
        bundled: dict[str, list[dict]],
        issue_ids: list[str],
    ) -> None:
        """Write cache rows from values_for_issues output. NEVER emits."""
        now = datetime.utcnow()
        for iid in issue_ids:
            entry = next(
                (x for x in (bundled.get(iid) or []) if x.get("key") == field.key),
                None,
            )
            if entry is None:
                continue
            await self._upsert_one_formula_cache(
                workspace_id=workspace_id,
                issue_id=iid,
                field_id=field.id,
                value_json=entry.get("value"),
                error=entry.get("error"),
                computed_at=now,
            )
        await self.db.commit()

    async def _upsert_one_formula_cache(
        self,
        *,
        workspace_id: str,
        issue_id: str,
        field_id: str,
        value_json: Any,
        error: str | None,
        computed_at: datetime | None = None,
    ) -> None:
        result = await self.db.execute(
            select(IssueFormulaCache).where(
                IssueFormulaCache.issue_id == issue_id,
                IssueFormulaCache.field_id == field_id,
            )
        )
        row = result.scalar_one_or_none()
        ts = computed_at or datetime.utcnow()
        if row is None:
            self.db.add(
                IssueFormulaCache(
                    workspace_id=workspace_id,
                    issue_id=issue_id,
                    field_id=field_id,
                    value_json=value_json,
                    error=error,
                    computed_at=ts,
                )
            )
        else:
            row.value_json = value_json
            row.error = error
            row.computed_at = ts
            row.workspace_id = workspace_id

    async def invalidate_formula_cache(
        self, *, workspace_id: str, field_id: str
    ) -> None:
        """Delete all cache rows for a formula field in the workspace. No emit."""
        await self.db.execute(
            delete(IssueFormulaCache).where(
                IssueFormulaCache.workspace_id == workspace_id,
                IssueFormulaCache.field_id == field_id,
            )
        )
        await self.db.commit()

    async def list_formula_fields(self, *, workspace_id: str) -> list[CustomField]:
        result = await self.db.execute(
            select(CustomField).where(
                CustomField.workspace_id == workspace_id,
                CustomField.type == "formula",
                CustomField.archived_at.is_(None),
            )
        )
        return list(result.scalars().all())

    def _formula_depends_on_cf_keys(
        self, field: CustomField, keys: set[str]
    ) -> bool:
        if not keys or field.type != "formula" or not field.formula_expr:
            return False
        try:
            parsed = parse_formula(field.formula_expr)
        except FormulaError:
            return False
        return bool(set(parsed.cf_keys) & keys)

    def _formula_depends_on_issue_attrs(
        self, field: CustomField, attrs: set[str]
    ) -> bool:
        """attrs subset of {priority,status,due_date,estimate_points,days_until_due}."""
        if not attrs or field.type != "formula" or not field.formula_expr:
            return False
        expr = field.formula_expr
        if "days_until_due" in attrs and "days_until_due" in expr:
            return True
        mapping = {
            "priority": "issue.priority",
            "status": "issue.status",
            "estimate_points": "issue.estimate_points",
            "due_date": "days_until_due",  # due_date feeds days_until_due
        }
        for a in attrs:
            token = mapping.get(a)
            if token and token in expr:
                return True
        return False

    async def refresh_formula_cache_for_issue(
        self,
        *,
        workspace_id: str,
        issue_id: str,
        depending_on_cf_keys: list[str] | None = None,
        depending_on_issue_attrs: list[str] | None = None,
        field_ids: list[str] | None = None,
    ) -> None:
        """Recompute and upsert formula cache rows. NEVER calls emit/webhook/timeline."""
        formulas = await self.list_formula_fields(workspace_id=workspace_id)
        if field_ids is not None:
            wanted = set(field_ids)
            formulas = [f for f in formulas if f.id in wanted]
        else:
            key_set = set(depending_on_cf_keys or [])
            attr_set = set(depending_on_issue_attrs or [])
            if key_set or attr_set:
                formulas = [
                    f
                    for f in formulas
                    if (key_set and self._formula_depends_on_cf_keys(f, key_set))
                    or (attr_set and self._formula_depends_on_issue_attrs(f, attr_set))
                ]
        if not formulas:
            return
        bundled = await self.values_for_issues(
            workspace_id=workspace_id, issue_ids=[issue_id]
        )
        now = datetime.utcnow()
        for field in formulas:
            entry = next(
                (x for x in (bundled.get(issue_id) or []) if x.get("key") == field.key),
                None,
            )
            if entry is None:
                continue
            await self._upsert_one_formula_cache(
                workspace_id=workspace_id,
                issue_id=issue_id,
                field_id=field.id,
                value_json=entry.get("value"),
                error=entry.get("error"),
                computed_at=now,
            )
        await self.db.commit()


def _formula_values_equal(actual: Any, expected: Any, result_type: str) -> bool:
    return _formula_values_compare(actual, "eq", expected, result_type)


def _formula_values_compare(
    actual: Any, op: str, expected: Any, result_type: str
) -> bool:
    if actual is None:
        return False
    op = (op or "eq").lower()
    if result_type == "number":
        try:
            a = float(actual)
            b = float(expected)
        except (TypeError, ValueError):
            return False
        if op == "eq":
            return a == b
        if op == "gt":
            return a > b
        if op == "gte":
            return a >= b
        if op == "lt":
            return a < b
        if op == "lte":
            return a <= b
        return False
    if result_type == "date":
        try:
            a = str(actual)
            b = str(expected)
        except Exception:
            return False
        if op == "eq":
            return a == b
        if op == "gt":
            return a > b
        if op == "gte":
            return a >= b
        if op == "lt":
            return a < b
        if op == "lte":
            return a <= b
        return False
    # text/boolean: eq only
    if op != "eq":
        return False
    return actual == expected


def _cf_range_type_ok(field: CustomField) -> bool:
    if field.type in ("number", "date"):
        return True
    if field.type == "formula":
        rt = (getattr(field, "formula_result_type", None) or "number").strip() or "number"
        return rt in ("number", "date")
    return False


def cf_value_range_clause(field: CustomField, op: str, expected: Any):
    """SQLAlchemy WHERE fragment for range compare on value_json (PG JSONB)."""
    from sqlalchemy import Float, String, Text, cast
    from sqlalchemy.dialects.postgresql import array as pg_array

    # empty text[] path → scalar root as text (5 → '5', "2026-01-01" → '2026-01-01')
    as_text = IssueCustomFieldValue.value_json.op("#>>")(pg_array([], type_=Text))
    if field.type == "number":
        lhs = cast(as_text, Float)
        rhs = float(expected)
    else:
        lhs = cast(as_text, String)
        rhs = str(expected)
    if op == "gt":
        return lhs > rhs
    if op == "gte":
        return lhs >= rhs
    if op == "lt":
        return lhs < rhs
    if op == "lte":
        return lhs <= rhs
    raise ValueError(f"unsupported range op: {op}")



# ---------------------------------------------------------------------------
# E32 · list / SmartSearch filters
# ---------------------------------------------------------------------------

_CF_BOOL_TRUE = {"true", "1", "yes", "y", "on"}
_CF_BOOL_FALSE = {"false", "0", "no", "n", "off"}


def _split_cf_key_op(raw_key: str) -> tuple[str, str] | None:
    """Return (key, op) or None if malformed / unknown bracket op."""
    key = (raw_key or "").strip().lower()
    if not key:
        return None
    m = _CF_KEY_OP_RE.match(key)
    if not m:
        return None
    return m.group(1), (m.group(2) or "eq")


def parse_cf_query_items(query_items: list[tuple[str, str]]) -> list[tuple[str, str, str]]:
    """Parse request query into [(field_key, op, raw_value), ...].

    Accepts (E32/E43/E46):
      - cf.<key>=value                 → op eq
      - cf.<key>[gt|gte|lt|lte]=value  → range op
      - cf=key=value / cf=key[op]=value
    """
    out: list[tuple[str, str, str]] = []
    for name, value in query_items:
        if name.startswith("cf.") and len(name) > 3:
            parsed = _split_cf_key_op(name[3:])
            if parsed:
                out.append((parsed[0], parsed[1], value))
            continue
        if name == "cf":
            raw = value or ""
            if "=" not in raw:
                continue
            key, _, rest = raw.partition("=")
            parsed = _split_cf_key_op(key)
            if parsed:
                out.append((parsed[0], parsed[1], rest))
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
    if t == "formula":
        rt = (getattr(field, "formula_result_type", None) or "number").strip() or "number"
        # Reuse storage-type coerce by temporarily viewing as result type
        proxy_type = rt if rt in ("number", "text", "boolean", "date") else "number"
        # Build a lightweight stand-in so we can recurse without mutating field
        class _Proxy:
            type = proxy_type
        return coerce_cf_filter_value(_Proxy(), raw)  # type: ignore[arg-type]
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
