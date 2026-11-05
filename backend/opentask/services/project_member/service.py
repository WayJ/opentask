"""E79: project lead + members roster service (roster-only; ≠ watchers; no ACL)."""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.project_member.model import ProjectMember
from opentask.models.requirement.model import Project
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import WorkspaceMember


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


def user_summary(u: UserModel | None, user_id: str) -> dict | None:
    """Soft-handle missing users: return None so callers can skip."""
    if u is None:
        return None
    return {
        "id": str(u.id),
        "name": getattr(u, "name", None),
        "sso_name": getattr(u, "sso_name", None),
        "sso_account": getattr(u, "sso_account", None),
    }


class ProjectMemberService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_project_in_workspace(self, *, project_id: str, workspace_id: str) -> Project:
        result = await self.db.execute(
            select(Project).where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在"
            )
        return project

    async def _assert_ws_member(self, *, workspace_id: str, user_id: str) -> None:
        q = await self.db.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == str(user_id),
            )
        )
        if q.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="必须为同工作区成员",
            )

    async def upsert_member(
        self,
        *,
        project_id: str,
        workspace_id: str,
        user_id: str,
        role: str | None = None,
    ) -> ProjectMember:
        existing = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == str(user_id),
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            return row
        row = ProjectMember(
            id=str(uuid4()),
            workspace_id=workspace_id,
            project_id=project_id,
            user_id=str(user_id),
            role=role,
            created_at=datetime.utcnow(),
        )
        self.db.add(row)
        await self.db.flush()
        return row

    async def set_lead(
        self,
        *,
        project_id: str,
        workspace_id: str,
        user_id: str | None,
    ) -> Project:
        project = await self.get_project_in_workspace(
            project_id=project_id, workspace_id=workspace_id
        )
        if user_id is None:
            project.lead_id = None
        else:
            await self._assert_ws_member(workspace_id=workspace_id, user_id=user_id)
            await self.upsert_member(
                project_id=project_id,
                workspace_id=workspace_id,
                user_id=user_id,
            )
            project.lead_id = str(user_id)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def add_member(
        self, *, project_id: str, workspace_id: str, user_id: str
    ) -> ProjectMember:
        await self.get_project_in_workspace(
            project_id=project_id, workspace_id=workspace_id
        )
        await self._assert_ws_member(workspace_id=workspace_id, user_id=user_id)
        row = await self.upsert_member(
            project_id=project_id,
            workspace_id=workspace_id,
            user_id=user_id,
        )
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def remove_member(
        self, *, project_id: str, workspace_id: str, user_id: str
    ) -> None:
        await self.get_project_in_workspace(
            project_id=project_id, workspace_id=workspace_id
        )
        existing = await self.db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == str(user_id),
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            await self.db.delete(row)
            await self.db.commit()

    async def list_member_rows(
        self, *, project_id: str, workspace_id: str
    ) -> list[ProjectMember]:
        await self.get_project_in_workspace(
            project_id=project_id, workspace_id=workspace_id
        )
        q = (
            select(ProjectMember)
            .where(
                ProjectMember.project_id == project_id,
                ProjectMember.workspace_id == workspace_id,
            )
            .order_by(ProjectMember.created_at.asc())
        )
        return list((await self.db.execute(q)).scalars().all())

    async def list_member_summaries(
        self, *, project_id: str, workspace_id: str
    ) -> list[dict]:
        rows = await self.list_member_rows(
            project_id=project_id, workspace_id=workspace_id
        )
        if not rows:
            return []
        user_ids = [str(r.user_id) for r in rows]
        uq = await self.db.execute(select(UserModel).where(UserModel.id.in_(user_ids)))
        users = {str(u.id): u for u in uq.scalars().all()}
        out: list[dict] = []
        for r in rows:
            summary = user_summary(users.get(str(r.user_id)), str(r.user_id))
            if summary is not None:
                out.append(summary)
        return out

    async def member_count(self, *, project_id: str) -> int:
        q = await self.db.execute(
            select(func.count())
            .select_from(ProjectMember)
            .where(ProjectMember.project_id == project_id)
        )
        return int(q.scalar_one() or 0)

    async def member_counts_for_projects(
        self, project_ids: list[str]
    ) -> dict[str, int]:
        if not project_ids:
            return {}
        q = await self.db.execute(
            select(ProjectMember.project_id, func.count())
            .where(ProjectMember.project_id.in_(project_ids))
            .group_by(ProjectMember.project_id)
        )
        return {str(pid): int(cnt) for pid, cnt in q.all()}

    async def resolve_lead_summary(self, lead_id: str | None) -> dict | None:
        if not lead_id:
            return None
        uq = await self.db.execute(select(UserModel).where(UserModel.id == str(lead_id)))
        u = uq.scalar_one_or_none()
        return user_summary(u, str(lead_id))

    async def enrich_show(self, project: Project) -> dict:
        """Full show payload extras (Q4a)."""
        lead_id = getattr(project, "lead_id", None)
        ws_id = project.workspace_id
        members: list[dict] = []
        count = 0
        if ws_id:
            members = await self.list_member_summaries(
                project_id=project.id, workspace_id=ws_id
            )
            count = len(members)
        else:
            count = await self.member_count(project_id=project.id)
        return {
            "lead_id": lead_id,
            "lead": await self.resolve_lead_summary(lead_id),
            "members": members,
            "member_count": count,
        }

    async def enrich_list_item(self, project: Project, counts: dict[str, int] | None = None) -> dict:
        """Slim list extras (Q4a)."""
        lead_id = getattr(project, "lead_id", None)
        if counts is not None:
            count = counts.get(project.id, 0)
        else:
            count = await self.member_count(project_id=project.id)
        return {"lead_id": lead_id, "member_count": count}
