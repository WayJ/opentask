"""Workspace 领域服务（E3-S1）"""
from __future__ import annotations

import hashlib
import re
import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.schemas.workspace import WorkspaceCreate, WorkspaceUpdate
from opentask.services.sla.business_hours import (
    normalize_business_hours,
    validate_timezone,
)
from opentask.services.workspace.issue_key import (
    derive_issue_key_from_slug,
    normalize_issue_key,
)

# E3 tenant seed — orphan when 0 members (E16 cleanup target)
DEFAULT_WORKSPACE_ID = "00000000-0000-4000-8000-000000000001"


_SLUG_RE = re.compile(r"[^a-z0-9-]+")


def slugify(name: str) -> str:
    base = name.strip().lower().replace(" ", "-")
    base = _SLUG_RE.sub("-", base).strip("-") or "workspace"
    return base[:60]


def _first_workspace_lock_key(user_id: str) -> int:
    """Stable signed int8 for pg_advisory_xact_lock. Not a workspace id."""
    digest = hashlib.sha256(f"opentask-first-workspace:{user_id}".encode()).digest()
    return int.from_bytes(digest[:8], "big", signed=True)


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
        issue_key: str | None = None,
    ) -> Workspace:
        final_slug = await self._unique_slug(slug or slugify(name))
        if issue_key:
            try:
                desired = normalize_issue_key(issue_key)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            clash = await self.session.execute(
                select(Workspace.id).where(Workspace.issue_key == desired).limit(1)
            )
            if clash.first() is not None:
                raise HTTPException(status_code=400, detail="issue_key 已被占用")
            issue_key = desired
        else:
            issue_key = await self._unique_issue_key(derive_issue_key_from_slug(final_slug))
        ws = Workspace(
            name=name.strip(),
            slug=final_slug,
            description=description,
            created_by=owner_user_id,
            issue_key=issue_key,
            issue_counter=0,
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

    async def _unique_issue_key(self, base: str) -> str:
        candidate = base
        n = 2
        for _ in range(32):
            exists = await self.session.execute(
                select(Workspace.id).where(Workspace.issue_key == candidate).limit(1)
            )
            if exists.first() is None:
                return candidate
            suffix = str(n)
            candidate = (base[: max(2, 6 - len(suffix))] + suffix)[:6]
            n += 1
        return f"OT{uuid.uuid4().hex[:4]}".upper()[:6]

    async def ensure_owner_workspace(
        self,
        *,
        owner_user_id: str,
        name: str = "OpenTask",
    ) -> tuple[Workspace, bool]:
        """Return this user's earliest usable workspace, creating one if needed.

        Usable matches ``list_for_user``: the legacy default workspace id is
        invisible and is never returned. A user whose only membership is that
        id gets a new workspace. An existing usable membership is kept; this
        does not join another user's workspace or insert a second membership.

        Concurrent callers for the same user take a transaction advisory lock
        and re-read memberships, so bootstrap and onboarding share one first
        workspace. ``create`` does not take this lock and can still add more.
        """
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": _first_workspace_lock_key(owner_user_id)},
        )
        existing = await self.list_for_user(owner_user_id)
        if existing:
            return existing[0][0], False
        created = await self.create_for_owner(name=name, owner_user_id=owner_user_id)
        return created, True

    async def list_for_user(self, user_id: str) -> list[tuple[Workspace, str]]:
        result = await self.session.execute(
            select(Workspace, WorkspaceMember.role)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.asc())
        )
        # Belt-and-suspenders: never surface the legacy orphan Default Workspace id
        return [
            (row[0], row[1])
            for row in result.all()
            if row[0].id != DEFAULT_WORKSPACE_ID
        ]

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
            issue_key=dto.issueKey,
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
        if dto.issueKey is not None:
            try:
                key = normalize_issue_key(dto.issueKey)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            if key != ws.issue_key:
                clash = await self.session.execute(
                    select(Workspace.id).where(
                        Workspace.issue_key == key,
                        Workspace.id != workspace_id,
                    ).limit(1)
                )
                if clash.first() is not None:
                    raise HTTPException(status_code=400, detail="issue_key 已被占用")
                ws.issue_key = key
                # E11-S4：改前缀后新单从 1 起；旧 Issue 保留原 issue_code
                ws.issue_counter = 0
        if dto.gitStatusHooksEnabled is not None:
            ws.git_status_hooks_enabled = bool(dto.gitStatusHooksEnabled)
        if dto.gitHookOnPrOpen is not None:
            ws.git_hook_on_pr_open = str(dto.gitHookOnPrOpen).strip() or "in_progress"
        if dto.gitHookOnPrMerged is not None:
            ws.git_hook_on_pr_merged = str(dto.gitHookOnPrMerged).strip() or "resolved"

        bh_changed = False
        if dto.timezone is not None:
            try:
                ws.timezone = validate_timezone(dto.timezone)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            bh_changed = True
        if dto.businessHours is not None:
            try:
                ws.business_hours = normalize_business_hours(dto.businessHours)
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e)) from e
            bh_changed = True
        ws.updated_at = datetime.utcnow()
        await self.session.flush()
        if bh_changed:
            from opentask.services.sla.service import SlaService
            await SlaService(self.session).recompute_deadlines_for_workspace(
                workspace_id=workspace_id
            )
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

    async def update_member_role(
        self, workspace_id: str, actor_id: str, target_user_id: str, role: str
    ) -> WorkspaceMember:
        await self.require_owner(workspace_id, actor_id)
        if role not in ("owner", "member", "viewer"):
            raise HTTPException(status_code=400, detail="无效角色")
        member = await self.get_membership(workspace_id, target_user_id)
        if member is None:
            raise HTTPException(status_code=404, detail="成员不存在")
        if member.role == "owner" and role != "owner":
            owners = await self.session.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.role == "owner",
                )
            )
            if len(list(owners.scalars().all())) <= 1:
                raise HTTPException(status_code=400, detail="不能降级唯一的 owner")
        member.role = role
        await self.session.commit()
        await self.session.refresh(member)
        return member

    async def leave(self, workspace_id: str, user_id: str) -> None:
        member = await self.get_membership(workspace_id, user_id)
        if member is None:
            raise HTTPException(status_code=404, detail="不是该工作区成员")
        if member.role == "owner":
            owners = await self.session.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == workspace_id,
                    WorkspaceMember.role == "owner",
                )
            )
            if len(list(owners.scalars().all())) <= 1:
                raise HTTPException(status_code=400, detail="唯一 owner 不能离开，请先转让")
        await self.session.delete(member)
        await self.session.commit()

    async def cleanup_orphan_default_workspace(self) -> dict:
        """E16: delete seeded Default Workspace when it has zero members.

        Detaches projects/issues first (SET workspace_id NULL) so FK does not block.
        Safe no-op if missing or still has members.
        """
        from opentask.models.issue.model import Issue
        from opentask.models.requirement.model import Project

        ws = await self.session.get(Workspace, DEFAULT_WORKSPACE_ID)
        if ws is None:
            return {"deleted": False, "reason": "missing"}

        member_count = await self.session.execute(
            select(func.count())
            .select_from(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == DEFAULT_WORKSPACE_ID)
        )
        n = int(member_count.scalar_one() or 0)
        if n > 0:
            return {"deleted": False, "reason": "has_members", "memberCount": n}

        await self.session.execute(
            update(Project)
            .where(Project.workspace_id == DEFAULT_WORKSPACE_ID)
            .values(workspace_id=None)
        )
        await self.session.execute(
            update(Issue)
            .where(Issue.workspace_id == DEFAULT_WORKSPACE_ID)
            .values(workspace_id=None)
        )
        await self.session.execute(
            delete(WorkspaceMember).where(
                WorkspaceMember.workspace_id == DEFAULT_WORKSPACE_ID
            )
        )
        await self.session.delete(ws)
        await self.session.flush()
        return {"deleted": True, "reason": "orphan", "id": DEFAULT_WORKSPACE_ID}

