"""Cycles API（E6-S1）"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.cycle.service import CycleService, require_writer, serialize_cycle
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/cycles", tags=["Cycles"])


class CycleCreate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    starts_at: datetime
    ends_at: datetime


class CycleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None


@router.get("")
async def list_cycles(
    status_filter: Optional[str] = Query(None, alias="status"),
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows = await CycleService(session).list(workspace_id=ws.id, status_filter=status_filter)
    return success_response(data={"rows": [serialize_cycle(r) for r in rows], "total": len(rows)})


@router.post("")
async def create_cycle(
    body: CycleCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row = await CycleService(session).create(
        workspace_id=ws.id,
        name=body.name,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
    )
    return success_response(data=serialize_cycle(row), message="Cycle 已创建")


@router.get("/{cycle_id}")
async def get_cycle(
    cycle_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    row = await CycleService(session).get(cycle_id, workspace_id=ws.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle 不存在")
    return success_response(data=serialize_cycle(row))


@router.patch("/{cycle_id}")
async def update_cycle(
    cycle_id: str,
    body: CycleUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = CycleService(session)
    row = await svc.get(cycle_id, workspace_id=ws.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle 不存在")
    row = await svc.update(row, name=body.name, starts_at=body.starts_at, ends_at=body.ends_at)
    return success_response(data=serialize_cycle(row), message="Cycle 已更新")


@router.delete("/{cycle_id}")
async def delete_cycle(
    cycle_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = CycleService(session)
    row = await svc.get(cycle_id, workspace_id=ws.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle 不存在")
    await svc.delete(row)
    return success_response(data={"id": cycle_id}, message="Cycle 已删除")


@router.post("/{cycle_id}/activate")
async def activate_cycle(
    cycle_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    svc = CycleService(session)
    row = await svc.get(cycle_id, workspace_id=ws.id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cycle 不存在")
    row = await svc.activate(row)
    return success_response(data=serialize_cycle(row), message="Cycle 已激活")
