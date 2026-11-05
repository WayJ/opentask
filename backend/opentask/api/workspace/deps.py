"""Workspace 请求上下文：X-Workspace-Id"""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.auth import authenticate
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.workspace.service import WorkspaceService


async def get_optional_workspace_context(
    x_workspace_id: Annotated[Optional[str], Header(alias="X-Workspace-Id")] = None,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
) -> tuple[Optional[Workspace], Optional[WorkspaceMember], UserModel]:
    """可选工作区上下文。

    - 未传头：返回 (None, None, user)，调用方按「成员可见 ∪ null」过滤
    - 传了头：校验成员资格，否则 403
    """
    if not x_workspace_id:
        return None, None, current_user
    svc = WorkspaceService(session)
    member = await svc.require_member(x_workspace_id, str(current_user.id))
    ws = await svc.get_or_404(x_workspace_id)
    return ws, member, current_user


async def require_workspace_context(
    x_workspace_id: Annotated[Optional[str], Header(alias="X-Workspace-Id")] = None,
    current_user: UserModel = Depends(authenticate),
    session: AsyncSession = Depends(get_session),
) -> tuple[Workspace, WorkspaceMember, UserModel]:
    if not x_workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少 X-Workspace-Id 请求头",
        )
    svc = WorkspaceService(session)
    member = await svc.require_member(x_workspace_id, str(current_user.id))
    ws = await svc.get_or_404(x_workspace_id)
    return ws, member, current_user


async def ensure_entity_workspace_access(
    session: AsyncSession,
    user_id: str,
    workspace_id: str | None,
) -> None:
    """E15：按实体自身 workspace_id 校验成员资格。

    - workspace_id 非空：非成员 → 403「无权访问该工作区」
    - workspace_id 为空（遗留孤儿行）：仅依赖路由层 authenticate，与列表「成员 ∪ NULL」一致
    """
    if not workspace_id:
        return
    await WorkspaceService(session).require_member(workspace_id, user_id)
