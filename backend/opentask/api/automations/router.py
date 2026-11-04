"""Automations API (E26)."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.automation.service import (
    AutomationService,
    require_writer,
    serialize_rule,
)
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/automations", tags=["Automations"])


class AutomationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    triggerType: str
    actionType: str
    triggerConfig: Optional[dict[str, Any]] = None
    condition: Optional[dict[str, Any]] = None
    actionConfig: Optional[dict[str, Any]] = None
    enabled: bool = True
    position: Optional[int] = None


class AutomationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    triggerType: Optional[str] = None
    triggerConfig: Optional[dict[str, Any]] = None
    setTriggerConfig: bool = False
    condition: Optional[dict[str, Any]] = None
    setCondition: bool = False
    actionType: Optional[str] = None
    actionConfig: Optional[dict[str, Any]] = None
    setActionConfig: bool = False
    enabled: Optional[bool] = None
    position: Optional[int] = None


@router.get("")
async def list_automations(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows = await AutomationService(session).list(workspace_id=ws.id)
    payload = [serialize_rule(r) for r in rows]
    return success_response(data={"rows": payload, "total": len(payload)})


@router.post("")
async def create_automation(
    body: AutomationCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    row = await AutomationService(session).create(
        workspace_id=ws.id,
        user_id=str(user.id),
        name=body.name,
        trigger_type=body.triggerType,
        action_type=body.actionType,
        trigger_config=body.triggerConfig,
        condition=body.condition,
        action_config=body.actionConfig,
        enabled=body.enabled,
        position=body.position,
    )
    return success_response(data=serialize_rule(row), message="已创建")


@router.get("/{rule_id}")
async def get_automation(
    rule_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    row = await AutomationService(session).get(workspace_id=ws.id, rule_id=rule_id)
    return success_response(data=serialize_rule(row))


@router.patch("/{rule_id}")
async def update_automation(
    rule_id: str,
    body: AutomationUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row = await AutomationService(session).update(
        workspace_id=ws.id,
        rule_id=rule_id,
        name=body.name,
        trigger_type=body.triggerType,
        trigger_config=body.triggerConfig,
        set_trigger_config=body.setTriggerConfig or body.triggerConfig is not None,
        condition=body.condition,
        set_condition=body.setCondition or body.condition is not None,
        action_type=body.actionType,
        action_config=body.actionConfig,
        set_action_config=body.setActionConfig or body.actionConfig is not None,
        enabled=body.enabled,
        position=body.position,
    )
    return success_response(data=serialize_rule(row), message="已更新")


@router.post("/{rule_id}/enable")
async def enable_automation(
    rule_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row = await AutomationService(session).set_enabled(
        workspace_id=ws.id, rule_id=rule_id, enabled=True
    )
    return success_response(data=serialize_rule(row), message="已启用")


@router.post("/{rule_id}/disable")
async def disable_automation(
    rule_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row = await AutomationService(session).set_enabled(
        workspace_id=ws.id, rule_id=rule_id, enabled=False
    )
    return success_response(data=serialize_rule(row), message="已禁用")


@router.delete("/{rule_id}")
async def delete_automation(
    rule_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    await AutomationService(session).delete(workspace_id=ws.id, rule_id=rule_id)
    return success_response(data={"id": rule_id}, message="已删除")
