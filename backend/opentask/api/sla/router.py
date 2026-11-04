"""SLA policies + run-due API (E42)."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.sla.service import (
    SlaService,
    require_owner,
    require_writer,
    serialize_policy,
)
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/sla", tags=["SLA"])


class PolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    startStatuses: list[str]
    stopStatuses: Optional[list[str]] = None
    targetMinutes: Optional[int] = 1440
    metric: str = "time_in_status"
    notifyAssignee: bool = True
    notifyWatchers: bool = False
    enabled: bool = True


class PolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=80)
    startStatuses: Optional[list[str]] = None
    stopStatuses: Optional[list[str]] = None
    targetMinutes: Optional[int] = None
    metric: Optional[str] = None
    notifyAssignee: Optional[bool] = None
    notifyWatchers: Optional[bool] = None
    enabled: Optional[bool] = None


@router.get("/policies")
async def list_policies(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows = await SlaService(session).list_policies(workspace_id=ws.id)
    payload = [serialize_policy(r) for r in rows]
    return success_response(data={"rows": payload, "total": len(payload)})


@router.post("/policies")
async def create_policy(
    body: PolicyCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_owner(member)
    row = await SlaService(session).create_policy(
        workspace_id=ws.id,
        name=body.name,
        start_statuses=body.startStatuses,
        stop_statuses=body.stopStatuses,
        target_minutes=body.targetMinutes if body.targetMinutes is not None else 1440,
        metric=body.metric,
        notify_assignee=body.notifyAssignee,
        notify_watchers=body.notifyWatchers,
        enabled=body.enabled,
    )
    return success_response(data=serialize_policy(row), message="已创建")


@router.patch("/policies/{policy_id}")
async def update_policy(
    policy_id: str,
    body: PolicyUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_owner(member)
    updates = body.model_dump(exclude_unset=True)
    # map camel keys already match service.update_policy
    row = await SlaService(session).update_policy(
        workspace_id=ws.id, policy_id=policy_id, updates=updates
    )
    return success_response(data=serialize_policy(row), message="已更新")


@router.delete("/policies/{policy_id}")
async def delete_policy(
    policy_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_owner(member)
    await SlaService(session).delete_policy(workspace_id=ws.id, policy_id=policy_id)
    return success_response(message="已删除")


@router.post("/run-due")
async def run_due_sla(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    """Mark overdue SLA clocks breached + Inbox. External tick — no in-process cron."""
    ws, member, user = ctx
    require_writer(member)
    result = await SlaService(session).run_due(
        workspace_id=ws.id,
        actor_user_id=str(user.id),
    )
    return success_response(data=result, message="已执行")
