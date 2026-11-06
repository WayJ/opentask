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
    WorkspaceMemberRoleUpdate,
    WorkspaceInviteCreate,
    WorkspaceUpdate,
)
from opentask.services.workspace.invite_service import InviteService

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
        "cyclesEnabled": bool(getattr(ws, "cycles_enabled", False)),
        "cycleDurationDays": int(getattr(ws, "cycle_duration_days", 14) or 14),
        "cycleRolloverPolicy": getattr(ws, "cycle_rollover_policy", None) or "into_next",
        "cycleCapacityLookback": int(getattr(ws, "cycle_capacity_lookback", 3) or 3),
        "issueKey": getattr(ws, "issue_key", None) or "OT",
        "gitStatusHooksEnabled": bool(getattr(ws, "git_status_hooks_enabled", False)),
        "gitHookOnPrOpen": getattr(ws, "git_hook_on_pr_open", None) or "in_progress",
        "gitHookOnPrMerged": getattr(ws, "git_hook_on_pr_merged", None) or "resolved",
        "timezone": getattr(ws, "timezone", None),
        "businessHours": getattr(ws, "business_hours", None) or {"enabled": False, "windows": {}},
        "appliedHolidayPacks": getattr(ws, "applied_holiday_packs", None) or [],
        "createdAt": ws.created_at,
        "updatedAt": ws.updated_at,
    }


@router.get("")
async def list_workspaces(
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    svc = WorkspaceService(session)
    # E16: lazily purge orphan Default Workspace seed on list
    try:
        await svc.cleanup_orphan_default_workspace()
        await session.commit()
    except Exception:
        await session.rollback()
    rows = await svc.list_for_user(str(current_user.id))
    return success_response(data=[_ws_out(ws, role) for ws, role in rows])


@router.post("")
async def create_workspace(
    dto: WorkspaceCreate,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    ws, role = await WorkspaceService(session).create(dto, str(current_user.id))
    return success_response(data=_ws_out(ws, role), message="工作区创建成功")


@router.post("/ensure-owner")
async def ensure_owner_workspace(
    dto: WorkspaceCreate,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    """Idempotent first workspace for bootstrap and empty-membership onboarding.

    A later POST /api/workspaces still creates another workspace.
    """
    svc = WorkspaceService(session)
    ws, _created = await svc.ensure_owner_workspace(
        owner_user_id=str(current_user.id),
        name=dto.name,
    )
    await session.commit()
    await session.refresh(ws)
    member = await svc.get_membership(ws.id, str(current_user.id))
    return success_response(data=_ws_out(ws, member.role if member else "owner"))


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


@router.patch("/{workspace_id}/members/{user_id}")
async def update_member_role(
    workspace_id: str,
    user_id: str,
    body: WorkspaceMemberRoleUpdate,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    member = await WorkspaceService(session).update_member_role(
        workspace_id, str(current_user.id), user_id, body.role
    )
    return success_response(
        data={
            "id": member.id,
            "userId": member.user_id,
            "role": member.role,
            "createdAt": member.created_at,
        },
        message="成员角色已更新",
    )


@router.post("/{workspace_id}/leave")
async def leave_workspace(
    workspace_id: str,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    await WorkspaceService(session).leave(workspace_id, str(current_user.id))
    return success_response(message="已离开工作区")


@router.post("/{workspace_id}/invites")
async def create_invite(
    workspace_id: str,
    body: WorkspaceInviteCreate,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    data = await InviteService(session).create(
        workspace_id,
        str(current_user.id),
        role=body.role,
        email=body.email,
        expires_in_days=body.expiresInDays or 14,
    )
    return success_response(data=data, message="邀请已创建")


@router.get("/{workspace_id}/invites")
async def list_invites(
    workspace_id: str,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    rows = await InviteService(session).list_for_workspace(workspace_id, str(current_user.id))
    return success_response(data=rows)


@router.delete("/{workspace_id}/invites/{invite_id}")
async def revoke_invite(
    workspace_id: str,
    invite_id: str,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    await InviteService(session).revoke(workspace_id, invite_id, str(current_user.id))
    return success_response(message="邀请已撤销")
