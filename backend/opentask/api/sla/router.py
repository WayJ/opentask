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
from opentask.services.sla.holiday_packs import list_packs, load_pack
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/sla", tags=["SLA"])


class PolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    startStatuses: list[str]
    stopStatuses: Optional[list[str]] = None
    pauseStatuses: Optional[list[str]] = None
    targetMinutes: Optional[int] = 1440
    metric: str = "time_in_status"
    notifyAssignee: bool = True
    notifyWatchers: bool = False
    enabled: bool = True
    calendar: Optional[dict[str, Any]] = None


class PolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=80)
    startStatuses: Optional[list[str]] = None
    stopStatuses: Optional[list[str]] = None
    pauseStatuses: Optional[list[str]] = None
    targetMinutes: Optional[int] = None
    metric: Optional[str] = None
    notifyAssignee: Optional[bool] = None
    notifyWatchers: Optional[bool] = None
    enabled: Optional[bool] = None
    calendar: Optional[dict[str, Any]] = None


@router.get("/policies")
async def list_policies(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows = await SlaService(session).list_policies(workspace_id=ws.id)
    payload = [serialize_policy(r, ws) for r in rows]
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
        pause_statuses=body.pauseStatuses,
        target_minutes=body.targetMinutes if body.targetMinutes is not None else 1440,
        metric=body.metric,
        notify_assignee=body.notifyAssignee,
        notify_watchers=body.notifyWatchers,
        enabled=body.enabled,
        calendar=body.calendar,
    )
    return success_response(data=serialize_policy(row, ws), message="已创建")


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
    # map camel keys already match service.update_policy; calendar=null clears overlay
    row = await SlaService(session).update_policy(
        workspace_id=ws.id, policy_id=policy_id, updates=updates
    )
    return success_response(data=serialize_policy(row, ws), message="已更新")


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


class HolidayPackTargetBody(BaseModel):
    target: str = "workspace"
    policyId: Optional[str] = None


@router.get("/holiday-packs")
async def holiday_packs_list(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
):
    """E58: list static packs (global read-only)."""
    _ws, _member, _user = ctx
    rows = list_packs()
    return success_response(data={"rows": rows, "total": len(rows)})


@router.get("/holiday-packs/{region}/{year}")
async def holiday_packs_show(
    region: str,
    year: int,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
):
    _ws, _member, _user = ctx
    try:
        pack = load_pack(region, year)
    except FileNotFoundError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e)) from e
    return success_response(data=pack)


@router.post("/holiday-packs/{region}/{year}/preview")
async def holiday_packs_preview(
    region: str,
    year: int,
    body: HolidayPackTargetBody | None = None,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    body = body or HolidayPackTargetBody()
    data = await SlaService(session).preview_holiday_pack(
        workspace=ws,
        region=region,
        year=year,
        target=body.target,
        policy_id=body.policyId,
    )
    return success_response(data=data)


@router.post("/holiday-packs/{region}/{year}/apply")
async def holiday_packs_apply(
    region: str,
    year: int,
    body: HolidayPackTargetBody | None = None,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_owner(member)
    body = body or HolidayPackTargetBody()
    data = await SlaService(session).apply_holiday_pack(
        workspace=ws,
        region=region,
        year=year,
        target=body.target,
        policy_id=body.policyId,
    )
    return success_response(data=data, message="已应用假日包")
