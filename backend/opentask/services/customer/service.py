"""Customer + CustomerRequest service (E22)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

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
)
from opentask.models.issue.model import Issue
from opentask.models.issue.schema import IssueCreate
from opentask.models.workspace.model import WorkspaceMember
from opentask.services.issue_service import IssueService


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


def serialize_request(
    row: CustomerRequest,
    *,
    issue_ids: list[str] | None = None,
    customer_name: str | None = None,
    issues: list[dict] | None = None,
) -> dict:
    data = {
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
    }
    if issues is not None:
        data["issues"] = issues
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
        return serialize_request(
            row, issue_ids=ids, customer_name=customer_name, issues=issues
        )
