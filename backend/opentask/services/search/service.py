"""E17/E60/E62: workspace-scoped global search aggregation."""
from __future__ import annotations

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.model import Issue
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import WorkspaceMember
from opentask.services.search.backend import (
    ISSUE_CODE_RE,
    resolve_search_backend,
)


class SearchService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.backend = resolve_search_backend(session)

    async def search(
        self, *, workspace_id: str, q: str, limit: int = 10
    ) -> dict[str, list[dict[str, Any]]]:
        query = (q or "").strip()
        if limit < 1:
            limit = 10
        if limit > 50:
            limit = 50
        if not query:
            return {"issues": [], "projects": [], "docs": [], "members": [], "comments": []}

        return {
            "issues": await self._search_issues(workspace_id, query, limit),
            "projects": await self.backend.search_projects(workspace_id, query, limit),
            "docs": await self.backend.search_docs(workspace_id, query, limit),
            "members": await self._search_members(workspace_id, query, limit),
            "comments": await self.backend.search_comments(workspace_id, query, limit),
        }

    async def _search_issues(
        self, workspace_id: str, query: str, limit: int
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()

        # Q5a / E17: exact issue_code first
        if ISSUE_CODE_RE.match(query):
            exact = await self.session.execute(
                select(Issue)
                .where(
                    Issue.workspace_id == workspace_id,
                    Issue.issue_code.ilike(query),
                )
                .limit(limit)
            )
            for issue in exact.scalars().all():
                if issue.id not in seen:
                    seen.add(issue.id)
                    rows.append(
                        {
                            "id": issue.id,
                            "issueCode": issue.issue_code,
                            "title": issue.title,
                            "status": issue.status.value
                            if hasattr(issue.status, "value")
                            else issue.status,
                            "priority": issue.priority.value
                            if hasattr(issue.priority, "value")
                            else issue.priority,
                            "rank": 1_000_000.0,
                        }
                    )

        fuzzy = await self.backend.search_issues(workspace_id, query, limit)
        for hit in fuzzy:
            hid = hit.get("id")
            if hid and hid not in seen and len(rows) < limit:
                seen.add(hid)
                rows.append(hit)

        return rows[:limit]

    async def _search_members(
        self, workspace_id: str, query: str, limit: int
    ) -> list[dict[str, Any]]:
        # Q2a: Members stay ILIKE
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
