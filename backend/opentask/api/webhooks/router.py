"""Outbound workspace webhooks API (E29)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.workspace_webhook.service import (
    WorkspaceWebhookService,
    require_owner,
    require_reader,
    serialize_delivery,
    serialize_webhook,
)
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])


class WebhookCreate(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    events: list[str] = Field(..., min_length=1)
    name: Optional[str] = Field(None, max_length=200)
    enabled: bool = True


class WebhookUpdate(BaseModel):
    url: Optional[str] = Field(None, min_length=1, max_length=2048)
    events: Optional[list[str]] = None
    name: Optional[str] = Field(None, max_length=200)
    setName: bool = False
    enabled: Optional[bool] = None


@router.get("")
async def list_webhooks(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_reader(member)
    rows = await WorkspaceWebhookService(session).list(workspace_id=ws.id)
    payload = [serialize_webhook(r) for r in rows]
    return success_response(data={"rows": payload, "total": len(payload)})


@router.post("")
async def create_webhook(
    body: WebhookCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_owner(member)
    row = await WorkspaceWebhookService(session).create(
        workspace_id=ws.id,
        user_id=str(user.id),
        url=body.url,
        events=body.events,
        name=body.name,
        enabled=body.enabled,
    )
    return success_response(
        data=serialize_webhook(row, include_secret=True),
        message="已创建；请妥善保存 secret（仅此一次返回）",
    )


@router.get("/{webhook_id}")
async def get_webhook(
    webhook_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_reader(member)
    row, logs = await WorkspaceWebhookService(session).get(
        workspace_id=ws.id, webhook_id=webhook_id, with_deliveries=True
    )
    return success_response(
        data=serialize_webhook(
            row, deliveries=[serialize_delivery(d) for d in logs]
        )
    )


@router.patch("/{webhook_id}")
async def update_webhook(
    webhook_id: str,
    body: WebhookUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_owner(member)
    row = await WorkspaceWebhookService(session).update(
        workspace_id=ws.id,
        webhook_id=webhook_id,
        url=body.url,
        events=body.events,
        name=body.name,
        set_name=body.setName or body.name is not None,
        enabled=body.enabled,
    )
    return success_response(data=serialize_webhook(row), message="已更新")


@router.delete("/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_owner(member)
    await WorkspaceWebhookService(session).delete(
        workspace_id=ws.id, webhook_id=webhook_id
    )
    return success_response(data={"id": webhook_id}, message="已删除")


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_owner(member)
    result = await WorkspaceWebhookService(session).test_deliver(
        workspace_id=ws.id, webhook_id=webhook_id
    )
    return success_response(data=result, message="已发送测试事件")
