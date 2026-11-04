"""Workspace 领域服务（E3-S1）"""
from __future__ import annotations

import re
import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def slugify(name: str) -> str:
    base = name.strip().lower().replace(" ", "-")
    base = _SLUG_RE.sub("-", base).strip("-") or "workspace"
    return base[:60]


class WorkspaceService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_for_owner(
        self,
        *,
        name: str,
        owner_user_id: str,
        slug: str | None = None,
        description: str | None = None,
    ) -> Workspace:
        final_slug = await self._unique_slug(slug or slugify(name))
        ws = Workspace(
            name=name.strip(),
            slug=final_slug,
            description=description,
            created_by=owner_user_id,
        )
        self.session.add(ws)
        await self.session.flush()
        self.session.add(
            WorkspaceMember(
                workspace_id=ws.id,
                user_id=owner_user_id,
                role="owner",
            )
        )
        await self.session.flush()
        return ws

    async def _unique_slug(self, base: str) -> str:
        candidate = base
        for _ in range(8):
            exists = await self.session.execute(
                select(Workspace.id).where(Workspace.slug == candidate).limit(1)
            )
            if exists.first() is None:
                return candidate
            candidate = f"{base[:50]}-{uuid.uuid4().hex[:6]}"
        return f"{base[:40]}-{uuid.uuid4().hex}"

    async def list_for_user(self, user_id: str) -> list[tuple[Workspace, str]]:
        result = await self.session.execute(
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.asc())
        )
        return [(row[0], row[1]) for row in result.all()]

    async def get_membership(self, workspace_id: str, user_id: str) -> WorkspaceMember | None:
        result = await self.session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_or_404(self, workspace_id: str) -> Workspace:
        result = await self.session.execute(
            select(Workspace).where(Workspace.id == workspace_id)
        )
        ws = result.scalar_one_or_none()
        if ws is None:
            raise HTTPException(status_code=404, detail="工作区不存在")
        return ws

    async def require_member(self, workspace_id: str, user_id: str) -> WorkspaceMember:
        member = await self.get_membership(workspace_id, user_id)
        if member is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该工作区")
        return member

    async def require_owner(self, workspace_id: str, user_id: str) -> WorkspaceMember:
        member = await self.require_member(workspace_id, user_id)
        if member.role != "owner":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅 owner 可执行此操作")
        return member

    async def create(self, dto: WorkspaceCreate, user_id: str) -> tuple[Workspace, str]:
        ws = await self.create_for_owner(
            name=dto.name,
            owner_user_id=user_id,
            slug=dto.slug,
            description=dto.description,
        )
        await self.session.commit()
        await self.session.refresh(ws)
        return ws, "owner"

    async def update(self, workspace_id: str, dto: WorkspaceUpdate, user_id: str) -> Workspace:
        await self.require_owner(workspace_id, user_id)
        ws = await self.get_or_404(workspace_id)
        if dto.name is not None:
            ws.name = dto.name.strip()
        if dto.description is not None:
            ws.description = dto.description
        if dto.cyclesEnabled is not None:
            ws.cycles_enabled = bool(dto.cyclesEnabled)
        if dto.cycleDurationDays is not None:
            ws.cycle_duration_days = int(dto.cycleDurationDays)
        if dto.cycleRolloverPolicy is not None:
            if dto.cycleRolloverPolicy not in ("into_next", "leave_unassigned"):
                raise HTTPException(status_code=400, detail="无效的 rollover 策略")
            ws.cycle_rollover_policy = dto.cycleRolloverPolicy
        if dto.cycleCapacityLookback is not None:
            ws.cycle_capacity_lookback = int(dto.cycleCapacityLookback)
        ws.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(ws)
        return ws

    async def list_members(self, workspace_id: str, user_id: str) -> list[WorkspaceMember]:
        await self.require_member(workspace_id, user_id)
        result = await self.session.execute(
            select(WorkspaceMember).where(WorkspaceMember.workspace_id == workspace_id)
        )
        return list(result.scalars().all())

    async def add_member(
        self, workspace_id: str, actor_id: str, target_user_id: str, role: str
    ) -> WorkspaceMember:
        await self.require_owner(workspace_id, actor_id)
        existing = await self.get_membership(workspace_id, target_user_id)
        if existing is not None:
            raise HTTPException(status_code=409, detail="用户已是工作区成员")
        member = WorkspaceMember(
            workspace_id=workspace_id,
            user_id=target_user_id,
            role=role,
        )
        self.session.add(member)
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def remove_member(self, workspace_id: str, actor_id: str, target_user_id: str) -> None:
        await self.require_owner(workspace_id, actor_id)
        member = await self.get_membership(workspace_id, target_user_id)
        if member is None:
            raise HTTPException(status_code=404, detail="成员不存在")
        if member.role == "owner":
            # 禁止移除最后一个 owner
            owners = await self.session.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.role == "owner",
                )
            )
            if len(list(owners.scalars().all())) <= 1:
                raise HTTPException(status_code=400, detail="不能移除唯一的 owner")
        await self.session.delete(member)
        await self.session.commit()

    async def member_workspace_ids(self, user_id: str) -> list[str]:
        result = await self.session.execute(
            select(WorkspaceMember.workspace_id).where(WorkspaceMember.user_id == user_id)
        )
        return [row[0] for row in result.all()]
