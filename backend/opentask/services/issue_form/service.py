"""Issue Form CRUD + public submit (E31)."""
from __future__ import annotations

import os
import re
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.custom_field import CustomField
from opentask.models.issue.enums import IssuePriority, IssueType
from opentask.models.issue.model import IssueTag
from opentask.models.issue.schema import IssueCreate
from opentask.models.issue_form.model import FORM_FIELD_TYPES, IssueForm
from opentask.models.tag.model import Tag
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import WorkspaceMember
from opentask.services.custom_field.service import CustomFieldService, validate_value
from opentask.services.issue_service import IssueService

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,78}[a-z0-9]$|^[a-z0-9]$")
PRIORITY_VALUES = {p.value for p in IssuePriority}

# token -> deque of timestamps (seconds)
_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_RATE_WINDOW_S = 60.0
_RATE_MAX = 30


def require_owner(member: WorkspaceMember) -> None:
    if member.role != "owner":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 owner 可管理表单",
        )


def require_reader(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可读表单",
        )


def _rate_limit_disabled() -> bool:
    return os.getenv("OPENTASK_FORM_RATE_LIMIT", "1").strip() in ("0", "false", "False", "off")


def check_rate_limit(token: str) -> None:
    if _rate_limit_disabled():
        return
    now = time.monotonic()
    bucket = _RATE_BUCKETS[token]
    while bucket and now - bucket[0] > _RATE_WINDOW_S:
        bucket.popleft()
    if len(bucket) >= _RATE_MAX:
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            detail="提交过于频繁，请稍后再试",
        )
    bucket.append(now)


def reset_rate_limit(token: str | None = None) -> None:
    if token is None:
        _RATE_BUCKETS.clear()
    else:
        _RATE_BUCKETS.pop(token, None)


def _new_token() -> str:
    return secrets.token_urlsafe(24)


def _normalize_slug(slug: str | None) -> str | None:
    if slug is None:
        return None
    s = slug.strip().lower()
    if not s:
        return None
    if not SLUG_RE.match(s):
        raise HTTPException(
            status_code=400,
            detail="slug 仅允许小写字母数字与中划线，且不以中划线开头/结尾",
        )
    return s


def validate_fields_schema(fields: list[Any] | None) -> list[dict]:
    if not fields or not isinstance(fields, list):
        raise HTTPException(status_code=400, detail="fields 必须为非空数组，且含 title")
    cleaned: list[dict] = []
    keys: set[str] = set()
    title_count = 0
    for i, raw in enumerate(fields):
        if not isinstance(raw, dict):
            raise HTTPException(status_code=400, detail=f"fields[{i}] 须为对象")
        ftype = str(raw.get("type") or "").strip()
        if ftype not in FORM_FIELD_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"fields[{i}].type 非法；允许: {', '.join(FORM_FIELD_TYPES)}",
            )
        key = str(raw.get("key") or ftype).strip()
        if not key or len(key) > 64:
            raise HTTPException(status_code=400, detail=f"fields[{i}].key 无效")
        if key in keys:
            raise HTTPException(status_code=400, detail=f"fields key 重复: {key}")
        keys.add(key)
        label = str(raw.get("label") or key).strip() or key
        required = bool(raw.get("required", ftype == "title"))
        entry: dict[str, Any] = {
            "key": key,
            "type": ftype,
            "label": label[:120],
            "required": required,
        }
        if raw.get("help"):
            entry["help"] = str(raw["help"])[:500]
        if ftype == "custom_field":
            cfid = raw.get("customFieldId") or raw.get("custom_field_id")
            if not cfid:
                raise HTTPException(
                    status_code=400,
                    detail=f"fields[{i}] custom_field 需要 customFieldId",
                )
            entry["customFieldId"] = str(cfid)
        if ftype == "title":
            title_count += 1
            entry["required"] = True
        cleaned.append(entry)
    if title_count != 1:
        raise HTTPException(status_code=400, detail="fields 必须恰好包含一个 type=title")
    return cleaned


def serialize_form(row: IssueForm, *, include_token: bool = True) -> dict:
    data: dict[str, Any] = {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "name": row.name,
        "slug": row.slug,
        "description": row.description,
        "enabled": bool(row.enabled),
        "fields": list(row.fields_json or []),
        "createCustomerRequest": bool(row.create_customer_request),
        "enqueueTriage": bool(row.enqueue_triage),
        "createdBy": row.created_by,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        "publicPath": f"/f/{row.token}",
    }
    if include_token:
        data["token"] = row.token
    return data


def serialize_public_schema(row: IssueForm) -> dict:
    return {
        "name": row.name,
        "description": row.description,
        "fields": list(row.fields_json or []),
        "enabled": True,
    }


class IssueFormService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, *, workspace_id: str) -> list[IssueForm]:
        q = (
            select(IssueForm)
            .where(IssueForm.workspace_id == workspace_id)
            .order_by(IssueForm.updated_at.desc())
        )
        return list((await self.db.execute(q)).scalars().all())

    async def get(self, *, workspace_id: str, form_id: str) -> IssueForm:
        q = select(IssueForm).where(
            IssueForm.id == form_id,
            IssueForm.workspace_id == workspace_id,
        )
        row = (await self.db.execute(q)).scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=404, detail="表单不存在")
        return row

    async def get_by_token(self, token: str, *, require_enabled: bool = True) -> IssueForm:
        q = select(IssueForm).where(IssueForm.token == token)
        row = (await self.db.execute(q)).scalar_one_or_none()
        if not row or (require_enabled and not row.enabled):
            raise HTTPException(status_code=404, detail="表单不存在或已禁用")
        return row

    async def _ensure_slug_unique(
        self, workspace_id: str, slug: str | None, *, exclude_id: str | None = None
    ) -> None:
        if not slug:
            return
        q = select(IssueForm).where(
            IssueForm.workspace_id == workspace_id,
            IssueForm.slug == slug,
        )
        if exclude_id:
            q = q.where(IssueForm.id != exclude_id)
        existing = (await self.db.execute(q)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=409, detail="slug 已存在")

    async def create(
        self,
        *,
        workspace_id: str,
        user_id: str,
        name: str,
        fields: list[Any],
        description: str | None = None,
        slug: str | None = None,
        enabled: bool = True,
        create_customer_request: bool = False,
        enqueue_triage: bool = False,
    ) -> IssueForm:
        name = (name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name 必填")
        fields_clean = validate_fields_schema(fields)
        slug_n = _normalize_slug(slug)
        await self._ensure_slug_unique(workspace_id, slug_n)
        row = IssueForm(
            workspace_id=workspace_id,
            name=name[:200],
            slug=slug_n,
            token=_new_token(),
            description=description,
            enabled=enabled,
            fields_json=fields_clean,
            create_customer_request=bool(create_customer_request),
            enqueue_triage=bool(enqueue_triage),
            created_by=user_id,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def update(
        self,
        *,
        workspace_id: str,
        form_id: str,
        name: str | None = None,
        description: str | None = None,
        clear_description: bool = False,
        slug: str | None = None,
        set_slug: bool = False,
        enabled: bool | None = None,
        fields: list[Any] | None = None,
        create_customer_request: bool | None = None,
        enqueue_triage: bool | None = None,
    ) -> IssueForm:
        row = await self.get(workspace_id=workspace_id, form_id=form_id)
        if name is not None:
            n = name.strip()
            if not n:
                raise HTTPException(status_code=400, detail="name 不能为空")
            row.name = n[:200]
        if clear_description:
            row.description = None
        elif description is not None:
            row.description = description
        if set_slug:
            slug_n = _normalize_slug(slug)
            await self._ensure_slug_unique(workspace_id, slug_n, exclude_id=row.id)
            row.slug = slug_n
        if enabled is not None:
            row.enabled = bool(enabled)
        if fields is not None:
            row.fields_json = validate_fields_schema(fields)
        if create_customer_request is not None:
            row.create_customer_request = bool(create_customer_request)
        if enqueue_triage is not None:
            row.enqueue_triage = bool(enqueue_triage)
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def delete(self, *, workspace_id: str, form_id: str) -> None:
        row = await self.get(workspace_id=workspace_id, form_id=form_id)
        await self.db.delete(row)
        await self.db.commit()

    async def regenerate_token(self, *, workspace_id: str, form_id: str) -> IssueForm:
        row = await self.get(workspace_id=workspace_id, form_id=form_id)
        old = row.token
        row.token = _new_token()
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        reset_rate_limit(old)
        return row

    async def _resolve_assignee(
        self, *, workspace_id: str, username: str
    ) -> str:
        uname = username.strip().lower()
        if not uname:
            raise HTTPException(status_code=400, detail="assignee 为空")
        user = (
            await self.db.execute(
                select(UserModel).where(UserModel.username == uname)
            )
        ).scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=400, detail=f"assignee 用户不存在: {uname}")
        member = (
            await self.db.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.user_id == str(user.id),
                )
            )
        ).scalar_one_or_none()
        if not member:
            raise HTTPException(
                status_code=400, detail=f"assignee 不是本工作区成员: {uname}"
            )
        return str(user.id)

    async def _resolve_labels(
        self, *, workspace_id: str, names: list[str]
    ) -> list[int]:
        ids: list[int] = []
        for name in names:
            n = str(name).strip()
            if not n:
                continue
            tag = (
                await self.db.execute(
                    select(Tag).where(Tag.workspace_id == workspace_id, Tag.name == n)
                )
            ).scalar_one_or_none()
            if not tag:
                raise HTTPException(status_code=400, detail=f"label 不存在: {n}")
            ids.append(int(tag.id))
        return ids

    async def submit(
        self,
        *,
        token: str,
        values: dict[str, Any],
    ) -> dict[str, Any]:
        check_rate_limit(token)
        form = await self.get_by_token(token, require_enabled=True)
        if not isinstance(values, dict):
            raise HTTPException(status_code=400, detail="values 须为对象")

        errors: list[dict[str, str]] = []
        parsed: dict[str, Any] = {}
        fields = list(form.fields_json or [])

        for field in fields:
            key = field["key"]
            ftype = field["type"]
            required = bool(field.get("required"))
            raw = values.get(key, values.get(ftype))
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                if required:
                    errors.append({"field": key, "message": f"{field.get('label') or key} 必填"})
                continue
            try:
                if ftype == "title":
                    title = str(raw).strip()
                    if not title:
                        raise ValueError("标题不能为空")
                    parsed["title"] = title[:255]
                elif ftype == "description":
                    parsed["description"] = str(raw)
                elif ftype == "priority":
                    p = str(raw).strip().lower()
                    if p not in PRIORITY_VALUES:
                        raise ValueError(
                            f"priority 须为 {', '.join(sorted(PRIORITY_VALUES))}"
                        )
                    parsed["priority"] = p
                elif ftype == "labels":
                    if isinstance(raw, str):
                        labels = [x.strip() for x in raw.split(",") if x.strip()]
                    elif isinstance(raw, list):
                        labels = [str(x).strip() for x in raw if str(x).strip()]
                    else:
                        raise ValueError("labels 须为数组或逗号分隔字符串")
                    parsed["label_ids"] = await self._resolve_labels(
                        workspace_id=form.workspace_id, names=labels
                    )
                elif ftype == "assignee":
                    parsed["assignee_id"] = await self._resolve_assignee(
                        workspace_id=form.workspace_id, username=str(raw)
                    )
                elif ftype == "custom_field":
                    cfid = field.get("customFieldId")
                    cf = (
                        await self.db.execute(
                            select(CustomField).where(
                                CustomField.id == cfid,
                                CustomField.workspace_id == form.workspace_id,
                                CustomField.archived_at.is_(None),
                            )
                        )
                    ).scalar_one_or_none()
                    if not cf:
                        raise ValueError("自定义字段不存在或已归档")
                    normalized = validate_value(cf, raw)
                    parsed.setdefault("custom_values", []).append(
                        {"fieldId": cf.id, "value": normalized}
                    )
                elif ftype == "customer_id":
                    parsed["customer_id"] = str(raw).strip()
            except HTTPException as he:
                detail = he.detail if isinstance(he.detail, str) else str(he.detail)
                errors.append({"field": key, "message": detail})
            except ValueError as ve:
                errors.append({"field": key, "message": str(ve)})

        if "title" not in parsed and not any(e["field"] for e in errors if True):
            # title field missing from values
            title_field = next((f for f in fields if f["type"] == "title"), None)
            if title_field:
                errors.append(
                    {
                        "field": title_field["key"],
                        "message": f"{title_field.get('label') or 'title'} 必填",
                    }
                )

        if errors:
            raise HTTPException(
                status_code=400,
                detail={"message": "校验失败", "errors": errors},
            )

        if "title" not in parsed:
            raise HTTPException(
                status_code=400,
                detail={"message": "校验失败", "errors": [{"field": "title", "message": "标题必填"}]},
            )

        actor = form.created_by
        if not actor:
            raise HTTPException(status_code=500, detail="表单缺少 created_by")

        issue_svc = IssueService(self.db)
        issue = await issue_svc.create_issue(
            IssueCreate(
                title=parsed["title"],
                description=parsed.get("description"),
                type=IssueType.FEEDBACK,
                priority=IssuePriority(parsed["priority"])
                if parsed.get("priority")
                else IssuePriority.MEDIUM,
                assignee_id=parsed.get("assignee_id"),
            ),
            user_id=actor,
            workspace_id=form.workspace_id,
        )

        for tag_id in parsed.get("label_ids") or []:
            exists = (
                await self.db.execute(
                    select(IssueTag).where(
                        IssueTag.issue_id == issue.id, IssueTag.tag_id == tag_id
                    )
                )
            ).scalar_one_or_none()
            if not exists:
                self.db.add(IssueTag(issue_id=issue.id, tag_id=tag_id))

        custom_values = parsed.get("custom_values") or []
        if custom_values:
            await CustomFieldService(self.db).upsert_issue_values(
                workspace_id=form.workspace_id,
                issue_id=str(issue.id),
                entries=custom_values,
            )

        request_id: str | None = None
        customer_id = parsed.get("customer_id")
        if form.create_customer_request and customer_id:
            from opentask.services.customer.service import CustomerRequestService

            try:
                req, _linked = await CustomerRequestService(self.db).create(
                    workspace_id=form.workspace_id,
                    user_id=actor,
                    customer_id=customer_id,
                    title=parsed["title"],
                    body=parsed.get("description"),
                    issue_ids=[str(issue.id)],
                )
                request_id = req.id
            except HTTPException:
                # 缺 customer 等：ADR D6 跳过不失败
                request_id = None

        await self.db.commit()
        await self.db.refresh(issue)

        return {
            "issueId": str(issue.id),
            "issueCode": issue.issue_code,
            "requestId": request_id,
            "title": issue.title,
        }
