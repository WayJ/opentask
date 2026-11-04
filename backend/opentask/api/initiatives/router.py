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
from opentask.services.initiative.service import (
    InitiativeService,
    require_writer,
    serialize_initiative,
)
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
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows = await InitiativeService(session).list(workspace_id=ws.id)
    return success_response(
        data={
            "rows": [serialize_initiative(r, pids) for r, pids in rows],
            "total": len(rows),
        }
    )


@router.post("")
async def create_initiative(
    body: InitiativeCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    row, pids = await InitiativeService(session).create(
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
    return success_response(data=serialize_initiative(row, pids), message="已创建")


@router.get("/{initiative_id}")
async def get_initiative(
    initiative_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    svc = InitiativeService(session)
    row = await svc.get(workspace_id=ws.id, initiative_id=initiative_id)
    pids = await svc._project_ids_for(row.id)
    return success_response(data=serialize_initiative(row, pids))


@router.patch("/{initiative_id}")
async def update_initiative(
    initiative_id: str,
    body: InitiativeUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row, pids = await InitiativeService(session).update(
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
    return success_response(data=serialize_initiative(row, pids), message="已更新")


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
    row, pids = await InitiativeService(session).set_projects(
        workspace_id=ws.id,
        initiative_id=initiative_id,
        project_ids=body.projectIds,
    )
    return success_response(data=serialize_initiative(row, pids), message="已更新关联项目")


@router.post("/{initiative_id}/projects/{project_id}")
async def attach_project(
    initiative_id: str,
    project_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row, pids = await InitiativeService(session).attach_project(
        workspace_id=ws.id,
        initiative_id=initiative_id,
        project_id=project_id,
    )
    return success_response(data=serialize_initiative(row, pids), message="已关联项目")


@router.delete("/{initiative_id}/projects/{project_id}")
async def detach_project(
    initiative_id: str,
    project_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row, pids = await InitiativeService(session).detach_project(
        workspace_id=ws.id,
        initiative_id=initiative_id,
        project_id=project_id,
    )
    return success_response(data=serialize_initiative(row, pids), message="已解除关联")
