"""Workspace CRUD API（E3-S1）"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import authenticate
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberAdd,
    WorkspaceUpdate,
)
from opentask.services.workspace.service import WorkspaceService
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/workspaces", tags=["Workspaces"])


def _ws_out(ws, role: str | None = None) -> dict:
    return {
        "id": ws.id,
        "name": ws.name,
        "slug": ws.slug,
        "description": ws.description,
        "role": role,
        "createdAt": ws.created_at,
        "updatedAt": ws.updated_at,
    }


@router.get("")
async def list_workspaces(
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    rows = await WorkspaceService(session).list_for_user(str(current_user.id))
    return success_response(data=[_ws_out(ws, role) for ws, role in rows])


@router.post("")
async def create_workspace(
    dto: WorkspaceCreate,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    ws, role = await WorkspaceService(session).create(dto, str(current_user.id))
    return success_response(data=_ws_out(ws, role), message="工作区创建成功")


@router.get("/{workspace_id}")
async def get_workspace(
    workspace_id: str,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    svc = WorkspaceService(session)
    member = await svc.require_member(workspace_id, str(current_user.id))
    ws = await svc.get_or_404(workspace_id)
    return success_response(data=_ws_out(ws, member.role))


@router.patch("/{workspace_id}")
async def update_workspace(
    workspace_id: str,
    dto: WorkspaceUpdate,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    ws = await WorkspaceService(session).update(workspace_id, dto, str(current_user.id))
    return success_response(data=_ws_out(ws, "owner"), message="工作区已更新")


@router.get("/{workspace_id}/members")
async def list_members(
    workspace_id: str,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    members = await WorkspaceService(session).list_members(workspace_id, str(current_user.id))
    data = [
        {
            "id": m.id,
            "userId": m.user_id,
            "role": m.role,
            "createdAt": m.created_at,
        }
        for m in members
    ]
    return success_response(data=data)


@router.post("/{workspace_id}/members")
async def add_member(
    workspace_id: str,
    body: WorkspaceMemberAdd,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    member = await WorkspaceService(session).add_member(
        workspace_id, str(current_user.id), body.userId, body.role
    )
    return success_response(
        data={
            "id": member.id,
            "userId": member.user_id,
            "role": member.role,
            "createdAt": member.created_at,
        },
        message="成员已添加",
    )


@router.delete("/{workspace_id}/members/{user_id}")
async def remove_member(
    workspace_id: str,
    user_id: str,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    await WorkspaceService(session).remove_member(workspace_id, str(current_user.id), user_id)
    return success_response(message="成员已移除")
