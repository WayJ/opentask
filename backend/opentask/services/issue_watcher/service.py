"""Issue watcher service (E18)"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.model import Issue
from opentask.models.issue_watcher.model import IssueWatcher


def serialize_watcher(w: IssueWatcher, *, username: str | None = None, name: str | None = None) -> dict:
    return {
        "id": w.id,
        "workspace_id": w.workspace_id,
        "issue_id": w.issue_id,
        "user_id": w.user_id,
        "username": username,
        "name": name,
        "created_at": w.created_at,
    }


async def enrich_watchers(db: AsyncSession, rows: list[IssueWatcher]) -> list[dict]:
    """Attach username/name for UI display."""
    from opentask.models.user.model import UserModel

    ids = [str(r.user_id) for r in rows if r.user_id]
    users: dict[str, UserModel] = {}
    if ids:
        q = await db.execute(select(UserModel).where(UserModel.id.in_(ids)))
        users = {str(u.id): u for u in q.scalars().all()}
    out = []
    for r in rows:
        u = users.get(str(r.user_id))
        out.append(
            serialize_watcher(
                r,
                username=getattr(u, "username", None) if u else None,
                name=(getattr(u, "name", None) or getattr(u, "sso_name", None)) if u else None,
            )
        )
    return out


class IssueWatcherService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_issue_in_workspace(self, *, issue_id: str, workspace_id: str) -> Issue:
        result = await self.db.execute(
            select(Issue).where(
                Issue.id == issue_id,
                Issue.workspace_id == workspace_id,
                Issue.is_deleted == False,  # noqa: E712
            )
        )
        issue = result.scalar_one_or_none()
        if not issue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Issue 不存在"
            )
        return issue

    async def list(self, *, issue_id: str, workspace_id: str) -> list[IssueWatcher]:
        await self.get_issue_in_workspace(issue_id=issue_id, workspace_id=workspace_id)
        q = (
            select(IssueWatcher)
            .where(
                IssueWatcher.issue_id == issue_id,
                IssueWatcher.workspace_id == workspace_id,
            )
            .order_by(IssueWatcher.created_at.asc())
        )
        return list((await self.db.execute(q)).scalars().all())

    async def watch(
        self, *, issue_id: str, workspace_id: str, user_id: str
    ) -> IssueWatcher:
        await self.get_issue_in_workspace(issue_id=issue_id, workspace_id=workspace_id)
        existing = await self.db.execute(
            select(IssueWatcher).where(
                IssueWatcher.issue_id == issue_id,
                IssueWatcher.user_id == str(user_id),
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            return row
        row = IssueWatcher(
            workspace_id=workspace_id,
            issue_id=issue_id,
            user_id=str(user_id),
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def unwatch(self, *, issue_id: str, workspace_id: str, user_id: str) -> None:
        await self.get_issue_in_workspace(issue_id=issue_id, workspace_id=workspace_id)
        existing = await self.db.execute(
            select(IssueWatcher).where(
                IssueWatcher.issue_id == issue_id,
                IssueWatcher.user_id == str(user_id),
            )
        )
        row = existing.scalar_one_or_none()
        if row:
            await self.db.delete(row)
            await self.db.commit()

    async def user_ids(self, *, issue_id: str) -> list[str]:
        q = await self.db.execute(
            select(IssueWatcher.user_id).where(IssueWatcher.issue_id == issue_id)
        )
        return [str(uid) for uid in q.scalars().all()]

    async def is_watching(self, *, issue_id: str, user_id: str) -> bool:
        q = await self.db.execute(
            select(IssueWatcher.id).where(
                IssueWatcher.issue_id == issue_id,
                IssueWatcher.user_id == str(user_id),
            )
        )
        return q.scalar_one_or_none() is not None
