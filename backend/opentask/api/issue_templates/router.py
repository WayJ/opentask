"""Issue Templates API (E9-S2)"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.issue_template.service import (
    IssueTemplateService,
    require_writer,
    serialize_issue_template,
)
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/issue-templates", tags=["Issue Templates"])


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=64)
    payload: Optional[dict[str, Any]] = None
    sortOrder: int = 0


class TemplateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=64)
    payload: Optional[dict[str, Any]] = None
    sortOrder: Optional[int] = None


@router.get("")
async def list_templates(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, user = ctx
    rows = await IssueTemplateService(session).list(
        workspace_id=ws.id, user_id=str(user.id), ensure=True
    )
    return success_response(
        data={"rows": [serialize_issue_template(r) for r in rows], "total": len(rows)}
    )


@router.post("/seed")
async def seed_templates(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    svc = IssueTemplateService(session)
    await svc.ensure_seeds(workspace_id=ws.id, user_id=str(user.id))
    rows = await svc.list(workspace_id=ws.id, ensure=False)
    return success_response(
        data={"rows": [serialize_issue_template(r) for r in rows], "total": len(rows)},
        message="种子模板已就绪",
    )


@router.post("")
async def create_template(
    body: TemplateCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    row = await IssueTemplateService(session).create(
        workspace_id=ws.id,
        user_id=str(user.id),
        name=body.name,
        description=body.description,
        icon=body.icon,
        payload=body.payload,
        sort_order=body.sortOrder,
    )
    return success_response(data=serialize_issue_template(row), message="模板已创建")


@router.patch("/{template_id}")
async def update_template(
    template_id: str,
    body: TemplateUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row = await IssueTemplateService(session).update(
        workspace_id=ws.id,
        template_id=template_id,
        name=body.name,
        description=body.description,
        icon=body.icon,
        payload=body.payload,
        sort_order=body.sortOrder,
    )
    return success_response(data=serialize_issue_template(row), message="模板已更新")


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    await IssueTemplateService(session).delete(
        workspace_id=ws.id, template_id=template_id
    )
    return success_response(data={"id": template_id}, message="模板已删除")
