"""Customer + CustomerRequest service (E22 + E63 public status)."""
from __future__ import annotations

import os
import secrets
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime
from typing import Any, Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.customer.model import (
    REQUEST_PRIORITIES,
    REQUEST_STATUSES,
    Customer,
    CustomerRequest,
    CustomerRequestIssue,
    CustomerRequestPublicReply,
)
from opentask.models.issue.enums import CommentType, TimelineAction
from opentask.models.issue.model import Issue, IssueComment
from opentask.models.issue.schema import IssueCreate
from opentask.models.workspace.model import WorkspaceMember
from opentask.services.issue_service import IssueService
from opentask.services.workspace_webhook.service import fire_webhooks


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


def serialize_customer(row: Customer, *, request_count: int | None = None) -> dict:
    data = {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "name": row.name,
        "domains": list(row.domains or []),
        "externalUrl": row.external_url,
        "notes": row.notes,
        "createdBy": row.created_by,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }
    if request_count is not None:
        data["requestCount"] = request_count
    return data


# E63 public status rate-limit (align E31: 30/60s/token)
_PUBLIC_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_RATE_WINDOW_S = 60.0
_RATE_MAX = 30


def _public_rate_limit_disabled() -> bool:
    return os.getenv("OPENTASK_PUBLIC_REQUEST_RATE_LIMIT", "1").strip() in (
        "0",
        "false",
        "False",
        "off",
    )


def check_public_rate_limit(token: str) -> None:
    if _public_rate_limit_disabled():
        return
    now = time.monotonic()
    bucket = _PUBLIC_RATE_BUCKETS[token]
    while bucket and now - bucket[0] > _RATE_WINDOW_S:
        bucket.popleft()
    if len(bucket) >= _RATE_MAX:
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
        )
    bucket.append(now)


def reset_public_rate_limit(token: str | None = None) -> None:
    if token is None:
        _PUBLIC_RATE_BUCKETS.clear()
    else:
        _PUBLIC_RATE_BUCKETS.pop(token, None)


def _new_status_token() -> str:
    return secrets.token_urlsafe(24)


def serialize_request(
    row: CustomerRequest,
    *,
    issue_ids: list[str] | None = None,
    customer_name: str | None = None,
    issues: list[dict] | None = None,
    include_token: bool = False,
    public_replies: list[dict] | None = None,
) -> dict:
    enabled = bool(getattr(row, "status_token_enabled", False))
    token = getattr(row, "status_token", None)
    data: dict[str, Any] = {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "customerId": row.customer_id,
        "customerName": customer_name,
        "title": row.title,
        "body": row.body,
        "status": row.status,
        "priority": row.priority,
        "issueIds": list(issue_ids or []),
        "issueCount": len(issue_ids or []),
        "createdBy": row.created_by,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
        "statusLink": {
            "enabled": enabled,
            "url": f"/r/{token}" if enabled and token else None,
            "publicRepliesEnabled": bool(getattr(row, "public_replies_enabled", False)),
        },
    }
    if issues is not None:
        data["issues"] = issues
    if public_replies is not None:
        data["publicReplies"] = public_replies
    if include_token and token:
        data["token"] = token
    return data


class CustomerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, *, workspace_id: str, customer_id: str) -> Customer:
        result = await self.db.execute(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.workspace_id == workspace_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="客户不存在")
        return row

    async def list(self, *, workspace_id: str) -> list[tuple[Customer, int]]:
        result = await self.db.execute(
            select(Customer)
            .where(Customer.workspace_id == workspace_id)
            .order_by(Customer.name.asc())
        )
        rows = list(result.scalars().all())
        if not rows:
            return []
        ids = [r.id for r in rows]
        count_result = await self.db.execute(
            select(CustomerRequest.customer_id, CustomerRequest.id).where(
                CustomerRequest.customer_id.in_(ids)
            )
        )
        counts: dict[str, int] = {i: 0 for i in ids}
        for cid, _rid in count_result.all():
            counts[cid] = counts.get(cid, 0) + 1
        return [(r, counts.get(r.id, 0)) for r in rows]

    async def create(
        self,
        *,
        workspace_id: str,
        user_id: str,
        name: str,
        domains: list[str] | None = None,
        external_url: str | None = None,
        notes: str | None = None,
    ) -> Customer:
        row = Customer(
            workspace_id=workspace_id,
            name=name.strip(),
            domains=list(domains or []),
            external_url=external_url,
            notes=notes,
            created_by=user_id,
        )
        self.db.add(row)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="同名客户已存在",
            )
        await self.db.refresh(row)
        return row

    async def update(
        self,
        *,
        workspace_id: str,
        customer_id: str,
        name: str | None = None,
        domains: list[str] | None = None,
        set_domains: bool = False,
        external_url: str | None = None,
        clear_external_url: bool = False,
        notes: str | None = None,
        clear_notes: bool = False,
    ) -> Customer:
        row = await self.get(workspace_id=workspace_id, customer_id=customer_id)
        if name is not None:
            row.name = name.strip()
        if set_domains:
            row.domains = list(domains or [])
        if clear_external_url:
            row.external_url = None
        elif external_url is not None:
            row.external_url = external_url
        if clear_notes:
            row.notes = None
        elif notes is not None:
            row.notes = notes
        row.updated_at = datetime.utcnow()
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail="同名客户已存在",
            )
        await self.db.refresh(row)
        return row

    async def delete(self, *, workspace_id: str, customer_id: str) -> None:
        row = await self.get(workspace_id=workspace_id, customer_id=customer_id)
        await self.db.delete(row)
        await self.db.commit()


class CustomerRequestService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _issue_ids_for(self, request_id: str) -> list[str]:
        result = await self.db.execute(
            select(CustomerRequestIssue.issue_id).where(
                CustomerRequestIssue.request_id == request_id
            )
        )
        return [r[0] for r in result.all()]

    async def _issue_ids_map(self, request_ids: list[str]) -> dict[str, list[str]]:
        if not request_ids:
            return {}
        result = await self.db.execute(
            select(CustomerRequestIssue.request_id, CustomerRequestIssue.issue_id).where(
                CustomerRequestIssue.request_id.in_(request_ids)
            )
        )
        out: dict[str, list[str]] = {i: [] for i in request_ids}
        for rid, iid in result.all():
            out.setdefault(rid, []).append(iid)
        return out

    async def _customer_names(self, customer_ids: list[str]) -> dict[str, str]:
        if not customer_ids:
            return {}
        result = await self.db.execute(
            select(Customer.id, Customer.name).where(Customer.id.in_(customer_ids))
        )
        return {cid: name for cid, name in result.all()}

    async def get(self, *, workspace_id: str, request_id: str) -> CustomerRequest:
        result = await self.db.execute(
            select(CustomerRequest).where(
                CustomerRequest.id == request_id,
                CustomerRequest.workspace_id == workspace_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="需求不存在")
        return row

    async def list(
        self,
        *,
        workspace_id: str,
        customer_id: str | None = None,
        status: str | None = None,
        issue_id: str | None = None,
    ) -> list[tuple[CustomerRequest, list[str], str | None]]:
        query = select(CustomerRequest).where(CustomerRequest.workspace_id == workspace_id)
        if customer_id:
            query = query.where(CustomerRequest.customer_id == customer_id)
        if status:
            query = query.where(CustomerRequest.status == status)
        if issue_id:
            query = query.join(
                CustomerRequestIssue,
                CustomerRequestIssue.request_id == CustomerRequest.id,
            ).where(CustomerRequestIssue.issue_id == issue_id)
        query = query.order_by(CustomerRequest.updated_at.desc())
        result = await self.db.execute(query)
        rows = list(result.scalars().unique().all())
        id_map = await self._issue_ids_map([r.id for r in rows])
        names = await self._customer_names([r.customer_id for r in rows])
        return [(r, id_map.get(r.id, []), names.get(r.customer_id)) for r in rows]

    async def _ensure_issue_in_ws(self, *, workspace_id: str, issue_id: str) -> Issue:
        result = await self.db.execute(
            select(Issue).where(Issue.id == issue_id, Issue.workspace_id == workspace_id)
        )
        issue = result.scalar_one_or_none()
        if not issue:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Issue 不存在")
        return issue

    async def create(
        self,
        *,
        workspace_id: str,
        user_id: str,
        customer_id: str,
        title: str,
        body: str | None = None,
        status: str = "open",
        priority: str | None = None,
        issue_ids: list[str] | None = None,
        create_and_link_issue: bool = False,
        project_id: str | None = None,
    ) -> tuple[CustomerRequest, list[str]]:
        if status not in REQUEST_STATUSES:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"status must be one of {REQUEST_STATUSES}",
            )
        if priority is not None and priority not in REQUEST_PRIORITIES:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"priority must be one of {REQUEST_PRIORITIES}",
            )
        # ensure customer in workspace
        cust_svc = CustomerService(self.db)
        await cust_svc.get(workspace_id=workspace_id, customer_id=customer_id)

        row = CustomerRequest(
            workspace_id=workspace_id,
            customer_id=customer_id,
            title=title.strip(),
            body=body,
            status=status,
            priority=priority,
            created_by=user_id,
        )
        self.db.add(row)
        await self.db.flush()

        linked: list[str] = []
        for iid in issue_ids or []:
            await self._ensure_issue_in_ws(workspace_id=workspace_id, issue_id=iid)
            self.db.add(CustomerRequestIssue(request_id=row.id, issue_id=iid))
            linked.append(iid)

        if create_and_link_issue:
            from opentask.models.issue.enums import IssueType

            issue_svc = IssueService(self.db)
            created = await issue_svc.create_issue(
                IssueCreate(
                    title=row.title,
                    description=body or "",
                    type=IssueType.FEATURE,
                    project_id=project_id,
                ),
                user_id=user_id,
                workspace_id=workspace_id,
            )
            self.db.add(CustomerRequestIssue(request_id=row.id, issue_id=created.id))
            linked.append(created.id)

        await self.db.commit()
        await self.db.refresh(row)
        return row, linked

    async def update(
        self,
        *,
        workspace_id: str,
        request_id: str,
        title: str | None = None,
        body: str | None = None,
        clear_body: bool = False,
        status: str | None = None,
        priority: str | None = None,
        clear_priority: bool = False,
        customer_id: str | None = None,
        public_replies_enabled: bool | None = None,
    ) -> tuple[CustomerRequest, list[str]]:
        row = await self.get(workspace_id=workspace_id, request_id=request_id)
        if title is not None:
            row.title = title.strip()
        if clear_body:
            row.body = None
        elif body is not None:
            row.body = body
        if status is not None:
            if status not in REQUEST_STATUSES:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"status must be one of {REQUEST_STATUSES}",
                )
            row.status = status
        if clear_priority:
            row.priority = None
        elif priority is not None:
            if priority not in REQUEST_PRIORITIES:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"priority must be one of {REQUEST_PRIORITIES}",
                )
            row.priority = priority
        if customer_id is not None:
            await CustomerService(self.db).get(workspace_id=workspace_id, customer_id=customer_id)
            row.customer_id = customer_id
        if public_replies_enabled is not None:
            row.public_replies_enabled = bool(public_replies_enabled)
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return row, await self._issue_ids_for(row.id)

    async def delete(self, *, workspace_id: str, request_id: str) -> None:
        row = await self.get(workspace_id=workspace_id, request_id=request_id)
        await self.db.delete(row)
        await self.db.commit()

    async def link_issue(
        self, *, workspace_id: str, request_id: str, issue_id: str
    ) -> tuple[CustomerRequest, list[str]]:
        row = await self.get(workspace_id=workspace_id, request_id=request_id)
        await self._ensure_issue_in_ws(workspace_id=workspace_id, issue_id=issue_id)
        existing = await self.db.execute(
            select(CustomerRequestIssue).where(
                CustomerRequestIssue.request_id == request_id,
                CustomerRequestIssue.issue_id == issue_id,
            )
        )
        if existing.scalar_one_or_none() is None:
            self.db.add(CustomerRequestIssue(request_id=request_id, issue_id=issue_id))
            await self.db.commit()
        return row, await self._issue_ids_for(request_id)

    async def unlink_issue(
        self, *, workspace_id: str, request_id: str, issue_id: str
    ) -> tuple[CustomerRequest, list[str]]:
        row = await self.get(workspace_id=workspace_id, request_id=request_id)
        await self.db.execute(
            delete(CustomerRequestIssue).where(
                CustomerRequestIssue.request_id == request_id,
                CustomerRequestIssue.issue_id == issue_id,
            )
        )
        await self.db.commit()
        return row, await self._issue_ids_for(request_id)

    async def to_response(
        self,
        row: CustomerRequest,
        issue_ids: list[str] | None = None,
        *,
        include_issues: bool = False,
        customer_name: str | None = None,
        include_token: bool = False,
        include_public_replies: bool = False,
    ) -> dict:
        ids = issue_ids if issue_ids is not None else await self._issue_ids_for(row.id)
        if customer_name is None:
            names = await self._customer_names([row.customer_id])
            customer_name = names.get(row.customer_id)
        issues: list[dict] | None = None
        if include_issues and ids:
            result = await self.db.execute(
                select(Issue).where(Issue.id.in_(ids), Issue.workspace_id == row.workspace_id)
            )
            issues = [
                {
                    "id": i.id,
                    "issueCode": i.issue_code,
                    "title": i.title,
                    "status": i.status,
                }
                for i in result.scalars().all()
            ]
        public_replies: list[dict] | None = None
        if include_public_replies or include_issues:
            public_replies = await self._list_public_replies(row.id)
        return serialize_request(
            row,
            issue_ids=ids,
            customer_name=customer_name,
            issues=issues,
            include_token=include_token,
            public_replies=public_replies,
        )

    async def _list_public_replies(self, request_id: str, *, limit: int = 50) -> list[dict]:
        result = await self.db.execute(
            select(CustomerRequestPublicReply)
            .where(CustomerRequestPublicReply.request_id == request_id)
            .order_by(CustomerRequestPublicReply.created_at.desc())
            .limit(limit)
        )
        rows = list(result.scalars().all())
        rows.reverse()
        return [
            {
                "id": r.id,
                "body": r.body,
                "createdAt": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    async def enable_status_link(
        self,
        *,
        workspace_id: str,
        request_id: str,
        public_replies_enabled: bool | None = None,
    ) -> CustomerRequest:
        row = await self.get(workspace_id=workspace_id, request_id=request_id)
        if not row.status_token:
            row.status_token = _new_status_token()
        row.status_token_enabled = True
        if public_replies_enabled is not None:
            row.public_replies_enabled = bool(public_replies_enabled)
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def rotate_status_link(
        self, *, workspace_id: str, request_id: str
    ) -> CustomerRequest:
        row = await self.get(workspace_id=workspace_id, request_id=request_id)
        old = row.status_token
        row.status_token = _new_status_token()
        row.status_token_enabled = True
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        if old:
            reset_public_rate_limit(old)
        return row

    async def revoke_status_link(
        self, *, workspace_id: str, request_id: str
    ) -> CustomerRequest:
        row = await self.get(workspace_id=workspace_id, request_id=request_id)
        old = row.status_token
        row.status_token = None
        row.status_token_enabled = False
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        if old:
            reset_public_rate_limit(old)
        return row

    async def get_by_status_token(self, token: str) -> CustomerRequest:
        if not token or not token.strip():
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="不存在")
        result = await self.db.execute(
            select(CustomerRequest).where(
                CustomerRequest.status_token == token.strip(),
                CustomerRequest.status_token_enabled == True,  # noqa: E712
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="不存在")
        return row

    async def serialize_public_card(self, row: CustomerRequest) -> dict:
        ids = await self._issue_ids_for(row.id)
        codes: list[str] = []
        if ids:
            result = await self.db.execute(
                select(Issue.issue_code)
                .where(Issue.id.in_(ids), Issue.workspace_id == row.workspace_id)
                .order_by(Issue.issue_code.asc())
            )
            codes = [c for (c,) in result.all() if c]
        names = await self._customer_names([row.customer_id])
        recent = await self._list_public_replies(row.id, limit=10)
        return {
            "title": row.title,
            "status": row.status,
            "priority": row.priority,
            "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
            "customerName": names.get(row.customer_id),
            "linkedIssueCount": len(ids),
            "linkedIssueCodes": codes,
            "publicRepliesEnabled": bool(row.public_replies_enabled),
            "recentPublicReplies": [
                {"body": r["body"], "createdAt": r["createdAt"]} for r in recent
            ],
        }

    async def add_public_reply(self, *, token: str, body: str) -> dict:
        text_body = (body or "").strip()
        if not text_body:
            raise HTTPException(status_code=400, detail="body 必填")
        if len(text_body) > 4000:
            raise HTTPException(status_code=400, detail="body 过长")
        row = await self.get_by_status_token(token)
        if not row.public_replies_enabled:
            raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="不存在")

        # First linked issue by link created_at ASC (Q3a)
        link_result = await self.db.execute(
            select(CustomerRequestIssue)
            .where(CustomerRequestIssue.request_id == row.id)
            .order_by(CustomerRequestIssue.created_at.asc())
            .limit(1)
        )
        link = link_result.scalar_one_or_none()
        if link is not None and row.created_by:
            issue = await self._ensure_issue_in_ws(
                workspace_id=row.workspace_id, issue_id=link.issue_id
            )
            author = row.created_by
            comment = IssueComment(
                issue_id=issue.id,
                user_id=author,
                content=text_body,
                comment_type=CommentType.COMMENT,
                meta_data={"source": "public_status_reply", "requestId": row.id},
            )
            self.db.add(comment)
            await self.db.flush()
            # light timeline + count (skip Inbox notify — Q5a)
            issue_svc = IssueService(self.db)
            await issue_svc._increment_comment_count(issue.id)
            await issue_svc._add_timeline(
                issue_id=issue.id,
                action_type=TimelineAction.COMMENTED,
                user_id=author,
                action_data={
                    "comment_id": comment.id,
                    "source": "public_status_reply",
                },
            )
            row.updated_at = datetime.utcnow()
            await self.db.commit()
            await fire_webhooks(
                self.db,
                workspace_id=row.workspace_id,
                event_type="comment.created",
                data={
                    "id": str(comment.id),
                    "issueId": str(issue.id),
                    "issueCode": issue.issue_code,
                    "source": "public_status_reply",
                },
            )
            return {
                "ok": True,
                "landedAs": "issue_comment",
                "issueId": issue.id,
                "issueCode": issue.issue_code,
                "commentId": comment.id,
            }

        reply = CustomerRequestPublicReply(
            id=str(uuid.uuid4()),
            request_id=row.id,
            body=text_body,
        )
        self.db.add(reply)
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        return {
            "ok": True,
            "landedAs": "public_reply",
            "replyId": reply.id,
        }
