"""Project Templates API (E72)"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.project_template.service import (
    ProjectTemplateService,
    require_writer,
    serialize_project_template,
)
from opentask.services.user_center.rbac_service import RbacService
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/project-templates", tags=["Project Templates"])


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


class ApplyBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    startsAt: Optional[datetime] = None


class FromProjectBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=64)


@router.get("")
async def list_templates(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows = await ProjectTemplateService(session).list(workspace_id=ws.id)
    return success_response(
        data={"rows": [serialize_project_template(r) for r in rows], "total": len(rows)}
    )


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    row = await ProjectTemplateService(session).get(
        workspace_id=ws.id, template_id=template_id
    )
    return success_response(data=serialize_project_template(row))


@router.post("")
async def create_template(
    body: TemplateCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    row = await ProjectTemplateService(session).create(
        workspace_id=ws.id,
        user_id=str(user.id),
        name=body.name,
        description=body.description,
        icon=body.icon,
        payload=body.payload,
        sort_order=body.sortOrder,
    )
    return success_response(data=serialize_project_template(row), message="模板已创建")


@router.patch("/{template_id}")
async def update_template(
    template_id: str,
    body: TemplateUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row = await ProjectTemplateService(session).update(
        workspace_id=ws.id,
        template_id=template_id,
        name=body.name,
        description=body.description,
        icon=body.icon,
        payload=body.payload,
        sort_order=body.sortOrder,
    )
    return success_response(data=serialize_project_template(row), message="模板已更新")


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    await ProjectTemplateService(session).delete(
        workspace_id=ws.id, template_id=template_id
    )
    return success_response(data={"id": template_id}, message="模板已删除")


@router.post("/{template_id}/apply")
async def apply_template(
    template_id: str,
    body: ApplyBody,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    dept_id = await RbacService(session).get_primary_dept_id(user)
    data = await ProjectTemplateService(session).apply(
        workspace_id=ws.id,
        template_id=template_id,
        name=body.name,
        description=body.description,
        starts_at=body.startsAt,
        user_id=str(user.id),
        dept_id=dept_id,
    )
    return success_response(data=data, message="已从模板创建项目")


@router.post("/from-project/{project_id}")
async def from_project(
    project_id: str,
    body: FromProjectBody,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    row = await ProjectTemplateService(session).from_project(
        workspace_id=ws.id,
        project_id=project_id,
        name=body.name,
        description=body.description,
        icon=body.icon,
        user_id=str(user.id),
    )
    return success_response(data=serialize_project_template(row), message="已另存为模板")
