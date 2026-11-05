"""Initiatives API (E10-S1) — Issue/Project axis; no PGE."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.initiative.model import INITIATIVE_STATUSES
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.initiative.service import InitiativeService, require_writer
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/initiatives", tags=["Initiatives"])


class InitiativeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    status: str = "active"
    targetDate: Optional[datetime] = None
    ownerUserId: Optional[str] = None
    sortOrder: int = 0
    projectIds: Optional[list[str]] = None

    @field_validator("status")
    @classmethod
    def _status(cls, v: str) -> str:
        if v not in INITIATIVE_STATUSES:
            raise ValueError(f"status must be one of {INITIATIVE_STATUSES}")
        return v


class InitiativeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    status: Optional[str] = None
    targetDate: Optional[datetime] = None
    clearTargetDate: bool = False
    ownerUserId: Optional[str] = None
    clearOwner: bool = False
    sortOrder: Optional[int] = None
    projectIds: Optional[list[str]] = None

    @field_validator("status")
    @classmethod
    def _status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in INITIATIVE_STATUSES:
            raise ValueError(f"status must be one of {INITIATIVE_STATUSES}")
        return v


class ProjectsBody(BaseModel):
    projectIds: list[str] = Field(default_factory=list)


@router.get("")
async def list_initiatives(
    include: Optional[str] = None,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    svc = InitiativeService(session)
    rows = await svc.list(workspace_id=ws.id)
    want_counts = bool(include and "relationCounts" in {p.strip() for p in include.split(",")})
    payload = [
        await svc.to_response(r, pids, include_relation_counts=want_counts)
        for r, pids in rows
    ]
    return success_response(data={"rows": payload, "total": len(payload)})


@router.post("")
async def create_initiative(
    body: InitiativeCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    svc = InitiativeService(session)
    row, pids = await svc.create(
        workspace_id=ws.id,
        user_id=str(user.id),
        name=body.name,
        description=body.description,
        status=body.status,
        target_date=body.targetDate,
        owner_user_id=body.ownerUserId,
        sort_order=body.sortOrder,
        project_ids=body.projectIds,
    )
    return success_response(data=await svc.to_response(row, pids), message="已创建")


@router.get("/{initiative_id}")
async def get_initiative(
    initiative_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    svc = InitiativeService(session)
    row = await svc.get(workspace_id=ws.id, initiative_id=initiative_id)
    return success_response(
        data=await svc.to_response(
            row, include_projects=True, include_relation_counts=True
        )
    )


@router.patch("/{initiative_id}")
async def update_initiative(
    initiative_id: str,
    body: InitiativeUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = InitiativeService(session)
    row, pids = await svc.update(
        workspace_id=ws.id,
        initiative_id=initiative_id,
        name=body.name,
        description=body.description,
        status=body.status,
        target_date=body.targetDate,
        clear_target_date=body.clearTargetDate,
        owner_user_id=body.ownerUserId,
        clear_owner=body.clearOwner,
        sort_order=body.sortOrder,
        project_ids=body.projectIds,
    )
    return success_response(data=await svc.to_response(row, pids, include_projects=True), message="已更新")


@router.delete("/{initiative_id}")
async def delete_initiative(
    initiative_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    await InitiativeService(session).delete(workspace_id=ws.id, initiative_id=initiative_id)
    return success_response(data={"id": initiative_id}, message="已删除")


@router.put("/{initiative_id}/projects")
async def set_projects(
    initiative_id: str,
    body: ProjectsBody,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = InitiativeService(session)
    row, pids = await svc.set_projects(
        workspace_id=ws.id,
        initiative_id=initiative_id,
        project_ids=body.projectIds,
    )
    return success_response(data=await svc.to_response(row, pids, include_projects=True), message="已更新关联项目")


@router.post("/{initiative_id}/projects/{project_id}")
async def attach_project(
    initiative_id: str,
    project_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = InitiativeService(session)
    row, pids = await svc.attach_project(
        workspace_id=ws.id,
        initiative_id=initiative_id,
        project_id=project_id,
    )
    return success_response(data=await svc.to_response(row, pids, include_projects=True), message="已关联项目")


@router.delete("/{initiative_id}/projects/{project_id}")
async def detach_project(
    initiative_id: str,
    project_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = InitiativeService(session)
    row, pids = await svc.detach_project(
        workspace_id=ws.id,
        initiative_id=initiative_id,
        project_id=project_id,
    )
    return success_response(data=await svc.to_response(row, pids, include_projects=True), message="已解除关联")


class RelationCreate(BaseModel):
    targetInitiativeId: str = Field(..., min_length=1)
    type: str = Field(..., min_length=1)


@router.get("/{initiative_id}/relations")
async def list_relations(
    initiative_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    svc = InitiativeService(session)
    items = await svc.list_relations(workspace_id=ws.id, initiative_id=initiative_id)
    return success_response(data={"items": items})


@router.post("/{initiative_id}/relations")
async def add_relation(
    initiative_id: str,
    body: RelationCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    svc = InitiativeService(session)
    item = await svc.add_relation(
        workspace_id=ws.id,
        initiative_id=initiative_id,
        target_initiative_id=body.targetInitiativeId,
        relation_type=body.type,
        user_id=str(user.id),
    )
    return success_response(data=item, message="已添加关系")


@router.delete("/{initiative_id}/relations/{relation_id}")
async def remove_relation(
    initiative_id: str,
    relation_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = InitiativeService(session)
    await svc.remove_relation(
        workspace_id=ws.id,
        initiative_id=initiative_id,
        relation_id=relation_id,
    )
    return success_response(data={"id": relation_id}, message="已删除关系")
