"""公开邀请预览 / 接受（E12-S2）"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import authenticate
from opentask.models.user.model import UserModel
from opentask.repositories.base import get_session
from opentask.services.workspace.invite_service import InviteService
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/invites", tags=["Invites"])


@router.get("/{token}")
async def preview_invite(
    token: str,
    session: AsyncSession = Depends(get_session),
):
    data = await InviteService(session).preview(token)
    return success_response(data=data)


@router.post("/{token}/accept")
async def accept_invite(
    token: str,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
):
    data = await InviteService(session).accept(token, str(current_user.id))
    return success_response(data=data, message="已加入工作区")
