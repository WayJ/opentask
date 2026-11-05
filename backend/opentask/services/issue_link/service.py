"""E76: Issue external links service — http(s) bookmarks on Issue."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from fastapi import HTTPException, status as http_status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.enums import TimelineAction
from opentask.models.issue.model import Issue, IssueTimeline
from opentask.models.issue_link.model import IssueLink
from opentask.models.workspace.model import WorkspaceMember

MAX_LINKS_PER_ISSUE = 50
MAX_URL_LEN = 2048
MAX_TITLE_LEN = 255


def validate_http_url(url: str) -> str:
    """Q4a: only http/https with a non-empty host; reject javascript:/relative/empty."""
    if url is None:
        raise ValueError("url 不能为空")
    normalized = url.strip()
    if not normalized:
        raise ValueError("url 不能为空")
    if len(normalized) > MAX_URL_LEN:
        raise ValueError(f"url 最长 {MAX_URL_LEN} 字符")
    parsed = urlparse(normalized)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("url 仅允许 http:// 或 https://")
    if not parsed.netloc:
        raise ValueError("url 缺少主机名")
    return normalized


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


def serialize_issue_link(row: IssueLink) -> dict:
    return {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "issueId": row.issue_id,
        "url": row.url,
        "title": row.title,
        "position": row.position,
        "createdBy": row.created_by,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


def _normalize_title(title: Optional[str]) -> Optional[str]:
    if title is None:
        return None
    cleaned = title.strip()
    if not cleaned:
        return None
    if len(cleaned) > MAX_TITLE_LEN:
        raise ValueError(f"title 最长 {MAX_TITLE_LEN} 字符")
    return cleaned


class IssueLinkService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_issue(self, *, workspace_id: str, issue_id: str) -> Issue:
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
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Issue 不存在或不属于当前工作区",
            )
        return issue

    async def list_links(self, *, workspace_id: str, issue_id: str) -> list[IssueLink]:
        await self.get_issue(workspace_id=workspace_id, issue_id=issue_id)
        result = await self.db.execute(
            select(IssueLink)
            .where(
                IssueLink.workspace_id == workspace_id,
                IssueLink.issue_id == issue_id,
            )
            .order_by(IssueLink.position.asc(), IssueLink.created_at.asc())
        )
        return list(result.scalars().all())

    async def _next_position(self, *, workspace_id: str, issue_id: str) -> int:
        result = await self.db.execute(
            select(func.coalesce(func.max(IssueLink.position), -1)).where(
                IssueLink.workspace_id == workspace_id,
                IssueLink.issue_id == issue_id,
            )
        )
        max_pos = result.scalar_one()
        return int(max_pos) + 1

    async def _count_links(self, *, workspace_id: str, issue_id: str) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(IssueLink)
            .where(
                IssueLink.workspace_id == workspace_id,
                IssueLink.issue_id == issue_id,
            )
        )
        return int(result.scalar_one())

    async def _add_timeline(
        self,
        *,
        issue_id: str,
        user_id: Optional[str],
        action_type: TimelineAction,
        action_data: Optional[dict] = None,
    ) -> None:
        self.db.add(
            IssueTimeline(
                issue_id=issue_id,
                user_id=user_id,
                action_type=action_type,
                action_data=action_data,
            )
        )

    async def create_link(
        self,
        *,
        workspace_id: str,
        issue_id: str,
        user_id: str,
        url: str,
        title: Optional[str] = None,
    ) -> IssueLink:
        await self.get_issue(workspace_id=workspace_id, issue_id=issue_id)
        normalized_url = validate_http_url(url)
        normalized_title = _normalize_title(title)
        count = await self._count_links(workspace_id=workspace_id, issue_id=issue_id)
        if count >= MAX_LINKS_PER_ISSUE:
            raise ValueError(f"每个 Issue 最多 {MAX_LINKS_PER_ISSUE} 条外链")
        position = await self._next_position(workspace_id=workspace_id, issue_id=issue_id)
        row = IssueLink(
            workspace_id=workspace_id,
            issue_id=issue_id,
            url=normalized_url,
            title=normalized_title,
            position=position,
            created_by=user_id,
        )
        self.db.add(row)
        await self.db.flush()
        await self._add_timeline(
            issue_id=issue_id,
            user_id=user_id,
            action_type=TimelineAction.LINK_ADDED,
            action_data={
                "link_id": row.id,
                "url": row.url,
                **({"title": row.title} if row.title else {}),
            },
        )
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def _get_link(
        self, *, workspace_id: str, issue_id: str, link_id: str
    ) -> IssueLink:
        result = await self.db.execute(
            select(IssueLink).where(
                IssueLink.id == link_id,
                IssueLink.workspace_id == workspace_id,
                IssueLink.issue_id == issue_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="外链不存在",
            )
        return row

    async def update_link(
        self,
        *,
        workspace_id: str,
        issue_id: str,
        link_id: str,
        url: Optional[str] = None,
        title: Optional[str] = None,
        position: Optional[int] = None,
    ) -> IssueLink:
        await self.get_issue(workspace_id=workspace_id, issue_id=issue_id)
        row = await self._get_link(
            workspace_id=workspace_id, issue_id=issue_id, link_id=link_id
        )
        if url is not None:
            row.url = validate_http_url(url)
        if title is not None:
            row.title = _normalize_title(title)
        if position is not None:
            if position < 0:
                raise ValueError("position 不能为负数")
            row.position = int(position)
        row.updated_at = datetime.utcnow()
        # Q5a: no timeline on title/url/position edits
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def delete_link(
        self,
        *,
        workspace_id: str,
        issue_id: str,
        link_id: str,
        user_id: str,
    ) -> None:
        await self.get_issue(workspace_id=workspace_id, issue_id=issue_id)
        row = await self._get_link(
            workspace_id=workspace_id, issue_id=issue_id, link_id=link_id
        )
        action_data = {
            "link_id": row.id,
            "url": row.url,
            **({"title": row.title} if row.title else {}),
        }
        await self.db.delete(row)
        await self._add_timeline(
            issue_id=issue_id,
            user_id=user_id,
            action_type=TimelineAction.LINK_REMOVED,
            action_data=action_data,
        )
        await self.db.commit()
