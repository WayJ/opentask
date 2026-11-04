"""Triage API（E9-S1 工作区入站队列）"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.triage.service import TriageService, require_writer
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/triage", tags=["Triage"])


class TriageEnqueueBody(BaseModel):
    issueId: Optional[str] = Field(None, min_length=1, max_length=36)
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[str] = Field("feedback")
    priority: Optional[str] = Field("medium")
    description: Optional[str] = None

    @model_validator(mode="after")
    def require_issue_or_title(self):
        if not self.issueId and not self.title:
            raise ValueError("必须提供 issueId 或 title")
        return self


class TriageDuplicateBody(BaseModel):
    duplicateOfIssueId: str = Field(..., min_length=1, max_length=36)


@router.get("")
async def list_triage(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows, total = await TriageService(session).list_pending(
        ws.id, page=page, page_size=page_size
    )
    return success_response(data={"rows": rows, "total": total})


@router.post("")
async def enqueue_or_create(
    body: TriageEnqueueBody,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    svc = TriageService(session)
    if body.issueId:
        row = await svc.enqueue(
            workspace_id=ws.id,
            issue_id=body.issueId,
            actor_user_id=str(user.id),
        )
        return success_response(data=row, message="已加入分诊队列")
    row = await svc.create_and_enqueue(
        workspace_id=ws.id,
        actor_user_id=str(user.id),
        title=body.title or "",
        type=body.type or "feedback",
        priority=body.priority or "medium",
        description=body.description,
    )
    return success_response(data=row, message="已创建并加入分诊队列")


@router.post("/{issue_id}/accept")
async def accept_triage(
    issue_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    row = await TriageService(session).accept(
        workspace_id=ws.id, issue_id=issue_id, actor_user_id=str(user.id)
    )
    return success_response(data=row, message="已接受")


@router.post("/{issue_id}/decline")
async def decline_triage(
    issue_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    row = await TriageService(session).decline(
        workspace_id=ws.id, issue_id=issue_id, actor_user_id=str(user.id)
    )
    return success_response(data=row, message="已拒绝")


@router.post("/{issue_id}/duplicate")
async def duplicate_triage(
    issue_id: str,
    body: TriageDuplicateBody,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    row = await TriageService(session).duplicate(
        workspace_id=ws.id,
        issue_id=issue_id,
        duplicate_of_issue_id=body.duplicateOfIssueId,
        actor_user_id=str(user.id),
    )
    return success_response(data=row, message="已标记重复")
