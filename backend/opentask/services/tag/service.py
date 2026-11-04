"""Tag / TagGroup 领域服务（E7-S1）"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from opentask.models.issue.model import Issue, IssueTag, IssueTimeline
from opentask.models.tag.model import Tag, TagGroup
from opentask.services.automation.service import fire_automations
from opentask.models.workspace.model import WorkspaceMember

DEFAULT_COLOR = "#3b82f6"


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写标签",
        )


def serialize_tag(t: Tag) -> dict:
    return {
        "id": t.id,
        "workspaceId": t.workspace_id,
        "name": t.name,
        "color": t.color,
        "groupId": t.group_id,
        "createdAt": t.created_at,
        "updatedAt": getattr(t, "updated_at", None),
    }


def serialize_tag_group(g: TagGroup) -> dict:
    return {
        "id": g.id,
        "workspaceId": g.workspace_id,
        "name": g.name,
        "color": g.color,
        "position": g.position,
        "createdAt": g.created_at,
        "updatedAt": g.updated_at,
    }


def serialize_tag_brief(t: Tag) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "color": t.color,
        "groupId": t.group_id,
    }


class TagService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_tags(
        self,
        *,
        workspace_id: str,
        group_id: Optional[str] = None,
        q: Optional[str] = None,
    ) -> list[Tag]:
        stmt = select(Tag).where(Tag.workspace_id == workspace_id)
        if group_id:
            stmt = stmt.where(Tag.group_id == group_id)
        if q:
            stmt = stmt.where(Tag.name.ilike(f"%{q.strip()}%"))
        stmt = stmt.order_by(Tag.name.asc())
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_tag(self, tag_id: int, *, workspace_id: str) -> Optional[Tag]:
        result = await self.db.execute(
            select(Tag).where(Tag.id == tag_id, Tag.workspace_id == workspace_id)
        )
        return result.scalar_one_or_none()

    async def create_tag(
        self,
        *,
        workspace_id: str,
        name: str,
        color: Optional[str] = None,
        group_id: Optional[str] = None,
    ) -> Tag:
        clean = (name or "").strip()
        if not clean:
            raise HTTPException(status_code=400, detail="标签名不能为空")
        if group_id:
            await self._require_group(group_id, workspace_id=workspace_id)
        now = datetime.utcnow()
        row = Tag(
            name=clean[:100],
            workspace_id=workspace_id,
            color=(color or DEFAULT_COLOR)[:20],
            group_id=group_id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="同工作区标签名已存在",
            ) from exc
        await self.db.refresh(row)
        return row

    async def update_tag(
        self,
        tag: Tag,
        *,
        name: Optional[str] = None,
        color: Optional[str] = None,
        group_id: Optional[str] = None,
        clear_group: bool = False,
    ) -> Tag:
        if name is not None:
            clean = name.strip()
            if not clean:
                raise HTTPException(status_code=400, detail="标签名不能为空")
            tag.name = clean[:100]
        if color is not None:
            tag.color = color[:20]
        if clear_group:
            tag.group_id = None
        elif group_id is not None:
            await self._require_group(group_id, workspace_id=tag.workspace_id)
            tag.group_id = group_id
        tag.updated_at = datetime.utcnow()
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="同工作区标签名已存在",
            ) from exc
        await self.db.refresh(tag)
        return tag

    async def delete_tag(self, tag: Tag) -> None:
        await self.db.delete(tag)
        await self.db.commit()

    async def list_groups(self, *, workspace_id: str) -> list[TagGroup]:
        stmt = (
            select(TagGroup)
            .where(TagGroup.workspace_id == workspace_id)
            .order_by(TagGroup.position.asc(), TagGroup.name.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_group(self, group_id: str, *, workspace_id: str) -> Optional[TagGroup]:
        result = await self.db.execute(
            select(TagGroup).where(
                TagGroup.id == group_id, TagGroup.workspace_id == workspace_id
            )
        )
        return result.scalar_one_or_none()

    async def create_group(
        self,
        *,
        workspace_id: str,
        name: str,
        color: Optional[str] = None,
        position: int = 0,
    ) -> TagGroup:
        clean = (name or "").strip()
        if not clean:
            raise HTTPException(status_code=400, detail="分组名不能为空")
        now = datetime.utcnow()
        row = TagGroup(
            workspace_id=workspace_id,
            name=clean[:64],
            color=(color[:20] if color else None),
            position=position,
            created_at=now,
            updated_at=now,
        )
        self.db.add(row)
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="同工作区分组名已存在",
            ) from exc
        await self.db.refresh(row)
        return row

    async def update_group(
        self,
        group: TagGroup,
        *,
        name: Optional[str] = None,
        color: Optional[str] = None,
        position: Optional[int] = None,
    ) -> TagGroup:
        if name is not None:
            clean = name.strip()
            if not clean:
                raise HTTPException(status_code=400, detail="分组名不能为空")
            group.name = clean[:64]
        if color is not None:
            group.color = color[:20] if color else None
        if position is not None:
            group.position = position
        group.updated_at = datetime.utcnow()
        try:
            await self.db.commit()
        except IntegrityError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="同工作区分组名已存在",
            ) from exc
        await self.db.refresh(group)
        return group

    async def delete_group(self, group: TagGroup) -> None:
        await self.db.delete(group)
        await self.db.commit()

    async def _require_group(self, group_id: str, *, workspace_id: str) -> TagGroup:
        group = await self.get_group(group_id, workspace_id=workspace_id)
        if not group:
            raise HTTPException(status_code=404, detail="标签组不存在")
        return group

    async def list_issue_tags(self, issue_id: str, *, workspace_id: str) -> list[Tag]:
        issue = await self._get_issue(issue_id, workspace_id=workspace_id)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue 不存在")
        stmt = (
            select(Tag)
            .join(IssueTag, IssueTag.tag_id == Tag.id)
            .where(IssueTag.issue_id == issue_id, Tag.workspace_id == workspace_id)
            .order_by(Tag.name.asc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def attach_tag(
        self,
        *,
        issue_id: str,
        tag_id: int,
        workspace_id: str,
        user_id: Optional[str] = None,
    ) -> Tag:
        issue = await self._get_issue(issue_id, workspace_id=workspace_id)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue 不存在")
        tag = await self.get_tag(tag_id, workspace_id=workspace_id)
        if not tag:
            raise HTTPException(status_code=404, detail="标签不存在")
        existing = await self.db.execute(
            select(IssueTag).where(
                IssueTag.issue_id == issue_id, IssueTag.tag_id == tag_id
            )
        )
        if existing.scalar_one_or_none():
            return tag
        self.db.add(IssueTag(issue_id=issue_id, tag_id=tag_id))
        self.db.add(
            IssueTimeline(
                issue_id=issue_id,
                user_id=user_id,
                action_type="label_added",
                action_data={"tag_id": tag_id, "label": tag.name},
            )
        )
        await self.db.commit()
        await fire_automations(
            self.db,
            workspace_id=workspace_id,
            trigger_type="label_added",
            issue=issue,
            actor_user_id=user_id,
            event={"tagId": tag_id, "label": tag.name},
        )
        return tag

    async def detach_tag(
        self,
        *,
        issue_id: str,
        tag_id: int,
        workspace_id: str,
        user_id: Optional[str] = None,
    ) -> None:
        issue = await self._get_issue(issue_id, workspace_id=workspace_id)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue 不存在")
        tag = await self.get_tag(tag_id, workspace_id=workspace_id)
        if not tag:
            raise HTTPException(status_code=404, detail="标签不存在")
        result = await self.db.execute(
            delete(IssueTag).where(
                IssueTag.issue_id == issue_id, IssueTag.tag_id == tag_id
            )
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="标签未关联")
        self.db.add(
            IssueTimeline(
                issue_id=issue_id,
                user_id=user_id,
                action_type="label_removed",
                action_data={"tag_id": tag_id, "label": tag.name},
            )
        )
        await self.db.commit()

    async def replace_issue_tags(
        self,
        *,
        issue_id: str,
        tag_ids: Sequence[int],
        workspace_id: str,
        user_id: Optional[str] = None,
    ) -> list[Tag]:
        issue = await self._get_issue(issue_id, workspace_id=workspace_id)
        if not issue:
            raise HTTPException(status_code=404, detail="Issue 不存在")
        desired = list(dict.fromkeys(int(x) for x in tag_ids))
        if desired:
            found = list(
                (
                    await self.db.execute(
                        select(Tag).where(
                            Tag.workspace_id == workspace_id, Tag.id.in_(desired)
                        )
                    )
                )
                .scalars()
                .all()
            )
            if len(found) != len(desired):
                raise HTTPException(status_code=404, detail="存在无效标签")
            by_id = {t.id: t for t in found}
        else:
            by_id = {}

        current = list(
            (
                await self.db.execute(
                    select(IssueTag).where(IssueTag.issue_id == issue_id)
                )
            )
            .scalars()
            .all()
        )
        current_ids = {it.tag_id for it in current}
        desired_set = set(desired)
        to_remove = current_ids - desired_set
        to_add = [tid for tid in desired if tid not in current_ids]

        if to_remove:
            await self.db.execute(
                delete(IssueTag).where(
                    IssueTag.issue_id == issue_id, IssueTag.tag_id.in_(list(to_remove))
                )
            )
            for tid in sorted(to_remove):
                tag = await self.get_tag(tid, workspace_id=workspace_id)
                self.db.add(
                    IssueTimeline(
                        issue_id=issue_id,
                        user_id=user_id,
                        action_type="label_removed",
                        action_data={
                            "tag_id": tid,
                            "label": tag.name if tag else None,
                        },
                    )
                )
        for tid in to_add:
            self.db.add(IssueTag(issue_id=issue_id, tag_id=tid))
            tag = by_id[tid]
            self.db.add(
                IssueTimeline(
                    issue_id=issue_id,
                    user_id=user_id,
                    action_type="label_added",
                    action_data={"tag_id": tid, "label": tag.name},
                )
            )
        await self.db.commit()
        for tid in to_add:
            tag = by_id.get(tid)
            await fire_automations(
                self.db,
                workspace_id=workspace_id,
                trigger_type="label_added",
                issue=issue,
                actor_user_id=user_id,
                event={"tagId": tid, "label": tag.name if tag else None},
            )
        return await self.list_issue_tags(issue_id, workspace_id=workspace_id)

    async def _get_issue(self, issue_id: str, *, workspace_id: str) -> Optional[Issue]:
        result = await self.db.execute(
            select(Issue).where(
                Issue.id == issue_id,
                Issue.workspace_id == workspace_id,
                Issue.is_deleted == False,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()


async def load_tags_for_issues(db: AsyncSession, issues: Sequence[Issue]) -> dict[str, list[Tag]]:
    """Batch load tags for issues (list enrichment)."""
    if not issues:
        return {}
    ids = [i.id for i in issues]
    stmt = (
        select(IssueTag.issue_id, Tag)
        .join(Tag, Tag.id == IssueTag.tag_id)
        .where(IssueTag.issue_id.in_(ids))
        .order_by(Tag.name.asc())
    )
    rows = (await db.execute(stmt)).all()
    out: dict[str, list[Tag]] = {i: [] for i in ids}
    for issue_id, tag in rows:
        out.setdefault(issue_id, []).append(tag)
    return out
