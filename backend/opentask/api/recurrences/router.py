"""Issue Recurrences API (E35)."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.issue_recurrence.service import (
    IssueRecurrenceService,
    require_writer,
    serialize_recurrence,
)
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/recurrences", tags=["Recurrences"])


class RecurrenceCreate(BaseModel):
    titleTemplate: str = Field(..., min_length=1, max_length=500)
    interval: str
    nextRunAt: str
    description: Optional[str] = None
    priority: Optional[str] = None
    labels: Optional[list[str]] = None
    projectId: Optional[str] = None
    assigneeId: Optional[str] = None
    customFields: Optional[dict[str, Any]] = None
    weekday: Optional[int] = None
    monthday: Optional[int] = None
    enabled: bool = True


class RecurrenceUpdate(BaseModel):
    titleTemplate: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    clearDescription: bool = False
    priority: Optional[str] = None
    setPriority: bool = False
    labels: Optional[list[str]] = None
    projectId: Optional[str] = None
    setProjectId: bool = False
    assigneeId: Optional[str] = None
    setAssigneeId: bool = False
    customFields: Optional[dict[str, Any]] = None
    interval: Optional[str] = None
    weekday: Optional[int] = None
    setWeekday: bool = False
    monthday: Optional[int] = None
    setMonthday: bool = False
    nextRunAt: Optional[str] = None
    enabled: Optional[bool] = None


@router.get("")
async def list_recurrences(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows = await IssueRecurrenceService(session).list(workspace_id=ws.id)
    payload = [serialize_recurrence(r) for r in rows]
    return success_response(data={"rows": payload, "total": len(payload)})


@router.post("")
async def create_recurrence(
    body: RecurrenceCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    row = await IssueRecurrenceService(session).create(
        workspace_id=ws.id,
        user_id=str(user.id),
        title_template=body.titleTemplate,
        interval=body.interval,
        next_run_at=body.nextRunAt,
        description=body.description,
        priority=body.priority,
        labels=body.labels,
        project_id=body.projectId,
        assignee_id=body.assigneeId,
        custom_fields=body.customFields,
        weekday=body.weekday,
        monthday=body.monthday,
        enabled=body.enabled,
    )
    return success_response(data=serialize_recurrence(row), message="已创建")


@router.post("/run-due")
async def run_due_recurrences(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    result = await IssueRecurrenceService(session).run_due(
        workspace_id=ws.id,
        actor_user_id=str(user.id),
    )
    return success_response(data=result, message="已执行")


@router.get("/{recurrence_id}")
async def get_recurrence(
    recurrence_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    row = await IssueRecurrenceService(session).get(
        workspace_id=ws.id, recurrence_id=recurrence_id
    )
    return success_response(data=serialize_recurrence(row))


@router.patch("/{recurrence_id}")
async def update_recurrence(
    recurrence_id: str,
    body: RecurrenceUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row = await IssueRecurrenceService(session).update(
        workspace_id=ws.id,
        recurrence_id=recurrence_id,
        title_template=body.titleTemplate,
        description=body.description,
        clear_description=body.clearDescription,
        priority=body.priority,
        set_priority=body.setPriority or body.priority is not None,
        labels=body.labels,
        project_id=body.projectId,
        set_project_id=body.setProjectId or body.projectId is not None,
        assignee_id=body.assigneeId,
        set_assignee_id=body.setAssigneeId or body.assigneeId is not None,
        custom_fields=body.customFields,
        interval=body.interval,
        weekday=body.weekday,
        set_weekday=body.setWeekday or body.weekday is not None,
        monthday=body.monthday,
        set_monthday=body.setMonthday or body.monthday is not None,
        next_run_at=body.nextRunAt,
        enabled=body.enabled,
    )
    return success_response(data=serialize_recurrence(row), message="已更新")


@router.delete("/{recurrence_id}")
async def delete_recurrence(
    recurrence_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    await IssueRecurrenceService(session).delete(
        workspace_id=ws.id, recurrence_id=recurrence_id
    )
    return success_response(data={"id": recurrence_id}, message="已删除")
