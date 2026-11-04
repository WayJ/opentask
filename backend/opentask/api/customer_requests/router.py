"""Customer Requests API (E22)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.customer.service import CustomerRequestService, require_writer
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/customer-requests", tags=["CustomerRequests"])


class RequestCreate(BaseModel):
    customerId: str
    title: str = Field(..., min_length=1, max_length=255)
    body: Optional[str] = None
    status: str = "open"
    priority: Optional[str] = None
    issueIds: Optional[list[str]] = None
    createAndLinkIssue: bool = False
    projectId: Optional[str] = None


class RequestUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    body: Optional[str] = None
    clearBody: bool = False
    status: Optional[str] = None
    priority: Optional[str] = None
    clearPriority: bool = False
    customerId: Optional[str] = None
    publicRepliesEnabled: Optional[bool] = None


class LinkIssueBody(BaseModel):
    issueId: str


@router.get("")
async def list_requests(
    customer_id: Optional[str] = Query(None, alias="customerId"),
    status: Optional[str] = Query(None),
    issue_id: Optional[str] = Query(None, alias="issueId"),
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    svc = CustomerRequestService(session)
    rows = await svc.list(
        workspace_id=ws.id,
        customer_id=customer_id,
        status=status,
        issue_id=issue_id,
    )
    payload = [
        await svc.to_response(r, ids, customer_name=name) for r, ids, name in rows
    ]
    return success_response(data={"rows": payload, "total": len(payload)})


@router.post("")
async def create_request(
    body: RequestCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    svc = CustomerRequestService(session)
    row, linked = await svc.create(
        workspace_id=ws.id,
        user_id=str(user.id),
        customer_id=body.customerId,
        title=body.title,
        body=body.body,
        status=body.status,
        priority=body.priority,
        issue_ids=body.issueIds,
        create_and_link_issue=body.createAndLinkIssue,
        project_id=body.projectId,
    )
    return success_response(
        data=await svc.to_response(row, linked, include_issues=True),
        message="已创建",
    )


@router.get("/{request_id}")
async def get_request(
    request_id: str,
    include_token: bool = Query(False, alias="include_token"),
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    svc = CustomerRequestService(session)
    row = await svc.get(workspace_id=ws.id, request_id=request_id)
    return success_response(
        data=await svc.to_response(
            row,
            include_issues=True,
            include_token=include_token,
            include_public_replies=True,
        )
    )


@router.patch("/{request_id}")
async def update_request(
    request_id: str,
    body: RequestUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = CustomerRequestService(session)
    row, ids = await svc.update(
        workspace_id=ws.id,
        request_id=request_id,
        title=body.title,
        body=body.body,
        clear_body=body.clearBody,
        status=body.status,
        priority=body.priority,
        clear_priority=body.clearPriority,
        customer_id=body.customerId,
        public_replies_enabled=body.publicRepliesEnabled,
    )
    return success_response(
        data=await svc.to_response(row, ids, include_issues=True),
        message="已更新",
    )


@router.delete("/{request_id}")
async def delete_request(
    request_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    await CustomerRequestService(session).delete(workspace_id=ws.id, request_id=request_id)
    return success_response(data={"id": request_id}, message="已删除")


@router.post("/{request_id}/issues")
async def link_issue(
    request_id: str,
    body: LinkIssueBody,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = CustomerRequestService(session)
    row, ids = await svc.link_issue(
        workspace_id=ws.id, request_id=request_id, issue_id=body.issueId
    )
    return success_response(
        data=await svc.to_response(row, ids, include_issues=True),
        message="已关联 Issue",
    )


@router.delete("/{request_id}/issues/{issue_id}")
async def unlink_issue(
    request_id: str,
    issue_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = CustomerRequestService(session)
    row, ids = await svc.unlink_issue(
        workspace_id=ws.id, request_id=request_id, issue_id=issue_id
    )
    return success_response(
        data=await svc.to_response(row, ids, include_issues=True),
        message="已解除关联",
    )


class StatusLinkEnableBody(BaseModel):
    publicRepliesEnabled: Optional[bool] = None


@router.post("/{request_id}/status-link/enable")
async def enable_status_link(
    request_id: str,
    body: StatusLinkEnableBody | None = None,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = CustomerRequestService(session)
    payload = body or StatusLinkEnableBody()
    row = await svc.enable_status_link(
        workspace_id=ws.id,
        request_id=request_id,
        public_replies_enabled=payload.publicRepliesEnabled,
    )
    return success_response(
        data=await svc.to_response(
            row, include_issues=True, include_token=True, include_public_replies=True
        ),
        message="已启用公开状态链接",
    )


@router.post("/{request_id}/status-link/rotate")
async def rotate_status_link(
    request_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = CustomerRequestService(session)
    row = await svc.rotate_status_link(workspace_id=ws.id, request_id=request_id)
    return success_response(
        data=await svc.to_response(
            row, include_issues=True, include_token=True, include_public_replies=True
        ),
        message="已轮换公开状态链接",
    )


@router.post("/{request_id}/status-link/revoke")
async def revoke_status_link(
    request_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = CustomerRequestService(session)
    row = await svc.revoke_status_link(workspace_id=ws.id, request_id=request_id)
    return success_response(
        data=await svc.to_response(
            row, include_issues=True, include_public_replies=True
        ),
        message="已撤销公开状态链接",
    )
