"""Workspace 邀请服务（E12-S2）"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.workspace.invite import WorkspaceInvite
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.services.workspace.service import WorkspaceService


def hash_invite_token(raw: str) -> str:
    return hashlib.sha256((raw or "").encode("utf-8")).hexdigest()


class InviteService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.ws = WorkspaceService(session)

    def _out(self, inv: WorkspaceInvite, *, token: str | None = None, workspace_name: str | None = None) -> dict:
        data = {
            "id": inv.id,
            "workspaceId": inv.workspace_id,
            "email": inv.email,
            "role": inv.role,
            "status": inv.status,
            "expiresAt": inv.expires_at,
            "invitedBy": inv.invited_by,
            "acceptedBy": inv.accepted_by,
            "acceptedAt": inv.accepted_at,
            "createdAt": inv.created_at,
        }
        if token is not None:
            data["token"] = token
        if workspace_name is not None:
            data["workspaceName"] = workspace_name
        return data

    async def create(
        self,
        workspace_id: str,
        actor_id: str,
        *,
        role: str = "member",
        email: str | None = None,
        expires_in_days: int = 14,
    ) -> dict:
        await self.ws.require_owner(workspace_id, actor_id)
        if role not in ("member", "viewer"):
            raise HTTPException(status_code=400, detail="邀请角色仅可为 member 或 viewer")
        days = int(expires_in_days or 14)
        if days < 1 or days > 90:
            raise HTTPException(status_code=400, detail="expiresInDays 须在 1–90")
        raw = secrets.token_urlsafe(32)
        inv = WorkspaceInvite(
            workspace_id=workspace_id,
            email=(email.strip() if email else None) or None,
            role=role,
            token_hash=hash_invite_token(raw),
            expires_at=datetime.utcnow() + timedelta(days=days),
            status="pending",
            invited_by=actor_id,
        )
        self.session.add(inv)
        await self.session.commit()
        await self.session.refresh(inv)
        return self._out(inv, token=raw)

    async def list_for_workspace(self, workspace_id: str, actor_id: str) -> list[dict]:
        await self.ws.require_owner(workspace_id, actor_id)
        result = await self.session.execute(
            select(WorkspaceInvite)
            .where(WorkspaceInvite.workspace_id == workspace_id)
            .order_by(WorkspaceInvite.created_at.desc())
            .limit(100)
        )
        return [self._out(inv) for inv in result.scalars().all()]

    async def revoke(self, workspace_id: str, invite_id: str, actor_id: str) -> None:
        await self.ws.require_owner(workspace_id, actor_id)
        inv = await self._get(invite_id)
        if inv is None or inv.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="邀请不存在")
        if inv.status == "pending":
            inv.status = "revoked"
            await self.session.commit()

    async def preview(self, raw_token: str) -> dict:
        inv = await self._by_token(raw_token)
        if inv is None:
            raise HTTPException(status_code=404, detail="邀请不存在")
        await self._refresh_expiry(inv)
        ws = await self.ws.get_or_404(inv.workspace_id)
        return self._out(inv, workspace_name=ws.name)

    async def accept(self, raw_token: str, user_id: str) -> dict:
        inv = await self._by_token(raw_token)
        if inv is None:
            raise HTTPException(status_code=404, detail="邀请不存在")
        await self._refresh_expiry(inv)
        if inv.status == "revoked":
            raise HTTPException(status_code=400, detail="邀请已撤销")
        if inv.status == "expired":
            raise HTTPException(status_code=400, detail="邀请已过期")
        existing = await self.ws.get_membership(inv.workspace_id, user_id)
        if existing is not None:
            # idempotent
            if inv.status == "pending":
                inv.status = "accepted"
                inv.accepted_by = user_id
                inv.accepted_at = datetime.utcnow()
                await self.session.commit()
            return {
                "workspaceId": inv.workspace_id,
                "userId": user_id,
                "role": existing.role,
                "alreadyMember": True,
            }
        if inv.status != "pending":
            raise HTTPException(status_code=400, detail="邀请不可接受")
        member = WorkspaceMember(
            workspace_id=inv.workspace_id,
            user_id=user_id,
            role=inv.role,
        )
        self.session.add(member)
        inv.status = "accepted"
        inv.accepted_by = user_id
        inv.accepted_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(member)
        return {
            "workspaceId": inv.workspace_id,
            "userId": user_id,
            "role": member.role,
            "alreadyMember": False,
        }

    async def accept_during_register(self, raw_token: str, user_id: str) -> str | None:
        """注册路径：失败不阻断注册；成功返回 workspace_id。"""
        if not raw_token:
            return None
        try:
            result = await self.accept(raw_token, user_id)
            return result["workspaceId"]
        except HTTPException:
            return None

    async def _get(self, invite_id: str) -> WorkspaceInvite | None:
        result = await self.session.execute(
            select(WorkspaceInvite).where(WorkspaceInvite.id == invite_id)
        )
        return result.scalar_one_or_none()

    async def _by_token(self, raw_token: str) -> WorkspaceInvite | None:
        th = hash_invite_token(raw_token)
        result = await self.session.execute(
            select(WorkspaceInvite).where(WorkspaceInvite.token_hash == th)
        )
        return result.scalar_one_or_none()

    async def _refresh_expiry(self, inv: WorkspaceInvite) -> None:
        if inv.status == "pending" and inv.expires_at <= datetime.utcnow():
            inv.status = "expired"
            await self.session.commit()
