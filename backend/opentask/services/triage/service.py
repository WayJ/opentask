"""Triage service — workspace intake queue (E9-S1)"""
from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.enums import RelationType
from opentask.models.issue.model import Issue
from opentask.models.issue.schema import IssueCreate
from opentask.models.workspace.model import WorkspaceMember
from opentask.services.issue_service import IssueService


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


def serialize_triage_issue(issue: Issue) -> dict:
    status_val = issue.status.value if hasattr(issue.status, "value") else issue.status
    type_val = issue.type.value if hasattr(issue.type, "value") else issue.type
    priority_val = issue.priority.value if hasattr(issue.priority, "value") else issue.priority
    return {
        "id": issue.id,
        "issueCode": issue.issue_code,
        "title": issue.title,
        "description": issue.description,
        "status": status_val,
        "type": type_val,
        "priority": priority_val,
        "triageStatus": issue.triage_status,
        "workspaceId": issue.workspace_id,
        "createdAt": issue.created_at.isoformat() if issue.created_at else None,
        "updatedAt": issue.updated_at.isoformat() if issue.updated_at else None,
    }


class TriageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_in_workspace(self, workspace_id: str, issue_id: str) -> Issue:
        result = await self.db.execute(
            select(Issue).where(
                Issue.id == issue_id,
                Issue.workspace_id == workspace_id,
                Issue.is_deleted.is_(False),
            )
        )
        issue = result.scalar_one_or_none()
        if not issue:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Issue 不存在"
            )
        return issue

    async def _require_pending(self, workspace_id: str, issue_id: str) -> Issue:
        issue = await self._get_in_workspace(workspace_id, issue_id)
        if issue.triage_status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Issue 不在 triage 队列中",
            )
        return issue

    async def list_pending(
        self, workspace_id: str, *, page: int = 1, page_size: int = 50
    ) -> tuple[list[dict], int]:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        conds = [
            Issue.workspace_id == workspace_id,
            Issue.triage_status == "pending",
            Issue.is_deleted.is_(False),
        ]
        total = (
            await self.db.execute(select(func.count()).select_from(Issue).where(*conds))
        ).scalar_one()
        result = await self.db.execute(
            select(Issue)
            .where(*conds)
            .order_by(Issue.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = [serialize_triage_issue(i) for i in result.scalars().all()]
        return rows, int(total)

    async def enqueue(
        self, *, workspace_id: str, issue_id: str, actor_user_id: str
    ) -> dict:
        issue = await self._get_in_workspace(workspace_id, issue_id)
        if issue.triage_status == "pending":
            return serialize_triage_issue(issue)
        issue.triage_status = "pending"
        issue.updated_by = actor_user_id
        await self.db.commit()
        await self.db.refresh(issue)
        return serialize_triage_issue(issue)

    async def create_and_enqueue(
        self,
        *,
        workspace_id: str,
        actor_user_id: str,
        title: str,
        type: str = "feedback",
        priority: str = "medium",
        description: str | None = None,
    ) -> dict:
        issue_svc = IssueService(self.db)
        data = IssueCreate(
            title=title,
            type=type,
            priority=priority,
            description=description,
            status="open",
            reporter_id=actor_user_id,
        )
        issue = await issue_svc.create_issue(
            data, user_id=actor_user_id, workspace_id=workspace_id
        )
        # create_issue commits; re-load and set triage
        issue = await self._get_in_workspace(workspace_id, issue.id)
        issue.triage_status = "pending"
        await self.db.commit()
        await self.db.refresh(issue)
        return serialize_triage_issue(issue)

    async def accept(self, *, workspace_id: str, issue_id: str, actor_user_id: str) -> dict:
        issue = await self._require_pending(workspace_id, issue_id)
        issue.status = "open"
        issue.triage_status = None
        issue.updated_by = actor_user_id
        await self.db.commit()
        await self.db.refresh(issue)
        return serialize_triage_issue(issue)

    async def decline(self, *, workspace_id: str, issue_id: str, actor_user_id: str) -> dict:
        issue = await self._require_pending(workspace_id, issue_id)
        issue.status = "rejected"
        issue.triage_status = None
        issue.updated_by = actor_user_id
        await self.db.commit()
        await self.db.refresh(issue)
        return serialize_triage_issue(issue)

    async def duplicate(
        self,
        *,
        workspace_id: str,
        issue_id: str,
        duplicate_of_issue_id: str,
        actor_user_id: str,
    ) -> dict:
        issue = await self._require_pending(workspace_id, issue_id)
        # canonical must be same workspace
        await self._get_in_workspace(workspace_id, duplicate_of_issue_id)
        if issue_id == duplicate_of_issue_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能将 Issue 标记为自身的重复",
            )
        issue_svc = IssueService(self.db)
        await issue_svc.add_relation(
            source_id=issue_id,
            target_id=duplicate_of_issue_id,
            relation_type=RelationType.DUPLICATES,
            user_id=actor_user_id,
        )
        # add_relation commits; re-load pending check may fail if we clear after —
        # re-fetch and apply decline semantics
        issue = await self._get_in_workspace(workspace_id, issue_id)
        issue.status = "rejected"
        issue.triage_status = None
        issue.updated_by = actor_user_id
        await self.db.commit()
        await self.db.refresh(issue)
        return serialize_triage_issue(issue)
