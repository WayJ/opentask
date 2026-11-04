"""E17: workspace-scoped global search aggregation."""
from __future__ import annotations

import re
from typing import Any, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.entity_document.model import EntityDocument
from opentask.models.issue.model import Issue
from opentask.models.requirement.model import Project
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import WorkspaceMember

ISSUE_CODE_RE = re.compile(
    r"^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$", re.IGNORECASE
)


class SearchService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(
        self, *, workspace_id: str, q: str, limit: int = 10
    ) -> dict[str, list[dict[str, Any]]]:
        query = (q or "").strip()
        if limit < 1:
            limit = 10
        if limit > 50:
            limit = 50
        if not query:
            return {"issues": [], "projects": [], "docs": [], "members": []}

        return {
            "issues": await self._search_issues(workspace_id, query, limit),
            "projects": await self._search_projects(workspace_id, query, limit),
            "docs": await self._search_docs(workspace_id, query, limit),
            "members": await self._search_members(workspace_id, query, limit),
        }

    async def _search_issues(
        self, workspace_id: str, query: str, limit: int
    ) -> list[dict[str, Any]]:
        pattern = f"%{query}%"
        rows: list[Issue] = []
        seen: set[str] = set()

        if ISSUE_CODE_RE.match(query):
            exact = await self.session.execute(
                select(Issue).where(
                    Issue.workspace_id == workspace_id,
                    or_(
                        Issue.issue_code.ilike(query),
                        Issue.legacy_issue_code.ilike(query),
                    ),
                ).limit(limit)
            )
            for issue in exact.scalars().all():
                if issue.id not in seen:
                    seen.add(issue.id)
                    rows.append(issue)

        fuzzy = await self.session.execute(
            select(Issue)
            .where(
                Issue.workspace_id == workspace_id,
                or_(
                    Issue.title.ilike(pattern),
                    Issue.issue_code.ilike(pattern),
                    Issue.legacy_issue_code.ilike(pattern),
                ),
            )
            .order_by(Issue.updated_at.desc())
            .limit(limit)
        )
        for issue in fuzzy.scalars().all():
            if issue.id not in seen and len(rows) < limit:
                seen.add(issue.id)
                rows.append(issue)

        return [
            {
                "id": i.id,
                "issueCode": i.issue_code,
                "title": i.title,
                "status": i.status.value if hasattr(i.status, "value") else i.status,
                "priority": i.priority.value if hasattr(i.priority, "value") else i.priority,
            }
            for i in rows[:limit]
        ]

    async def _search_projects(
        self, workspace_id: str, query: str, limit: int
    ) -> list[dict[str, Any]]:
        pattern = f"%{query}%"
        result = await self.session.execute(
            select(Project)
            .where(
                Project.workspace_id == workspace_id,
                Project.name.ilike(pattern),
            )
            .order_by(Project.name.asc())
            .limit(limit)
        )
        return [
            {
                "id": p.id,
                "name": p.name,
                "description": (p.description or "")[:160],
                "isActive": bool(p.is_active),
            }
            for p in result.scalars().all()
        ]

    async def _search_docs(
        self, workspace_id: str, query: str, limit: int
    ) -> list[dict[str, Any]]:
        pattern = f"%{query}%"
        result = await self.session.execute(
            select(EntityDocument)
            .where(
                EntityDocument.workspace_id == workspace_id,
                or_(
                    EntityDocument.title.ilike(pattern),
                    EntityDocument.body_md.ilike(pattern),
                ),
            )
            .order_by(EntityDocument.updated_at.desc())
            .limit(limit)
        )
        return [
            {
                "id": d.id,
                "title": d.title,
                "parentType": d.parent_type,
                "parentId": d.parent_id,
                "snippet": (d.body_md or "").strip().replace("\n", " ")[:120],
            }
            for d in result.scalars().all()
        ]

    async def _search_members(
        self, workspace_id: str, query: str, limit: int
    ) -> list[dict[str, Any]]:
        pattern = f"%{query}%"
        result = await self.session.execute(
            select(WorkspaceMember, UserModel)
            .join(UserModel, UserModel.id == WorkspaceMember.user_id)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                or_(
                    UserModel.username.ilike(pattern),
                    UserModel.name.ilike(pattern),
                    UserModel.sso_name.ilike(pattern),
                    UserModel.sso_account.ilike(pattern),
                ),
            )
            .limit(limit)
        )
        out: list[dict[str, Any]] = []
        for member, user in result.all():
            out.append(
                {
                    "membershipId": member.id,
                    "userId": member.user_id,
                    "role": member.role,
                    "username": user.username,
                    "name": user.name or user.sso_name or user.username,
                }
            )
        return out
