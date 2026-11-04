"""Issue VCS links service (E11-S1) — Issue axis only."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import HTTPException, status as http_status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.model import Issue
from opentask.models.issue_vcs_link.model import (
    VCS_LINK_KINDS,
    VCS_LINK_STATUSES,
    VCS_PROVIDERS,
    IssueVcsLink,
)
from opentask.models.workspace.model import WorkspaceMember
from opentask.services.vcs.branch_naming import slugify_title, suggest_branch_name


def require_writer(member: WorkspaceMember) -> None:
    if member.role not in ("owner", "member"):
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="仅 member/owner 可写",
        )


def serialize_vcs_link(row: IssueVcsLink) -> dict:
    return {
        "id": row.id,
        "workspaceId": row.workspace_id,
        "issueId": row.issue_id,
        "kind": row.kind,
        "branchName": row.branch_name,
        "prUrl": row.pr_url,
        "provider": row.provider,
        "externalId": row.external_id,
        "status": row.status,
        "repoConfigId": row.repo_config_id,
        "title": row.title,
        "createdBy": row.created_by,
        "createdAt": row.created_at.isoformat() if row.created_at else None,
        "updatedAt": row.updated_at.isoformat() if row.updated_at else None,
    }


class IssueVcsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_issue(self, *, workspace_id: str, issue_id: str) -> Issue:
        result = await self.db.execute(
            select(Issue).where(Issue.id == issue_id, Issue.workspace_id == workspace_id)
        )
        issue = result.scalar_one_or_none()
        if not issue:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Issue 不存在或不属于当前工作区",
            )
        return issue

    async def branch_name(self, *, workspace_id: str, issue_id: str) -> dict:
        issue = await self.get_issue(workspace_id=workspace_id, issue_id=issue_id)
        slug = slugify_title(issue.title)
        branch = suggest_branch_name(issue.issue_code, issue.title)
        return {
            "branchName": branch,
            "issueCode": issue.issue_code,
            "slug": slug,
            "issueId": issue.id,
        }

    async def list_links(self, *, workspace_id: str, issue_id: str) -> list[IssueVcsLink]:
        await self.get_issue(workspace_id=workspace_id, issue_id=issue_id)
        result = await self.db.execute(
            select(IssueVcsLink)
            .where(
                IssueVcsLink.workspace_id == workspace_id,
                IssueVcsLink.issue_id == issue_id,
            )
            .order_by(IssueVcsLink.updated_at.desc())
        )
        return list(result.scalars().all())

    async def create_link(
        self,
        *,
        workspace_id: str,
        issue_id: str,
        user_id: str,
        kind: str,
        branch_name: Optional[str] = None,
        pr_url: Optional[str] = None,
        provider: str = "manual",
        external_id: Optional[str] = None,
        status: str = "unknown",
        title: Optional[str] = None,
        repo_config_id: Optional[int] = None,
    ) -> IssueVcsLink:
        await self.get_issue(workspace_id=workspace_id, issue_id=issue_id)
        if kind not in VCS_LINK_KINDS:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"kind 仅允许: {', '.join(VCS_LINK_KINDS)}",
            )
        if provider not in VCS_PROVIDERS:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"provider 仅允许: {', '.join(VCS_PROVIDERS)}",
            )
        if status not in VCS_LINK_STATUSES:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"status 仅允许: {', '.join(VCS_LINK_STATUSES)}",
            )
        if kind == "branch" and not (branch_name or "").strip():
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="kind=branch 需要 branchName",
            )
        if kind == "pull_request" and not (pr_url or "").strip():
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="kind=pull_request 需要 prUrl",
            )
        row = IssueVcsLink(
            workspace_id=workspace_id,
            issue_id=issue_id,
            kind=kind,
            branch_name=(branch_name or None),
            pr_url=(pr_url or None),
            provider=provider,
            external_id=external_id,
            status=status,
            repo_config_id=repo_config_id,
            title=title,
            created_by=user_id,
        )
        self.db.add(row)
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def delete_link(self, *, workspace_id: str, issue_id: str, link_id: str) -> None:
        await self.get_issue(workspace_id=workspace_id, issue_id=issue_id)
        result = await self.db.execute(
            select(IssueVcsLink).where(
                IssueVcsLink.id == link_id,
                IssueVcsLink.workspace_id == workspace_id,
                IssueVcsLink.issue_id == issue_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND, detail="VCS link 不存在"
            )
        await self.db.delete(row)
        await self.db.commit()


    async def update_link(
        self,
        *,
        workspace_id: str,
        issue_id: str,
        link_id: str,
        branch_name: Optional[str] = None,
        pr_url: Optional[str] = None,
        provider: Optional[str] = None,
        external_id: Optional[str] = None,
        status: Optional[str] = None,
        title: Optional[str] = None,
    ) -> IssueVcsLink:
        await self.get_issue(workspace_id=workspace_id, issue_id=issue_id)
        result = await self.db.execute(
            select(IssueVcsLink).where(
                IssueVcsLink.id == link_id,
                IssueVcsLink.workspace_id == workspace_id,
                IssueVcsLink.issue_id == issue_id,
            )
        )
        row = result.scalar_one_or_none()
        if not row:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND, detail="VCS link 不存在"
            )
        if status is not None:
            if status not in VCS_LINK_STATUSES:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"status 仅允许: {', '.join(VCS_LINK_STATUSES)}",
                )
            row.status = status
        if branch_name is not None:
            row.branch_name = branch_name
        if pr_url is not None:
            row.pr_url = pr_url
        if provider is not None:
            if provider not in VCS_PROVIDERS:
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=f"provider 仅允许: {', '.join(VCS_PROVIDERS)}",
                )
            row.provider = provider
        if external_id is not None:
            row.external_id = external_id
        if title is not None:
            row.title = title
        row.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(row)
        return row

    async def find_issue_by_code(self, issue_code: str) -> Issue | None:
        result = await self.db.execute(
            select(Issue).where(
                (Issue.issue_code == issue_code) | (Issue.legacy_issue_code == issue_code)
            )
        )
        return result.scalar_one_or_none()

    async def find_link_by_pr(
        self, *, pr_url: str | None = None, external_id: str | None = None
    ) -> IssueVcsLink | None:
        if pr_url:
            result = await self.db.execute(
                select(IssueVcsLink).where(
                    IssueVcsLink.kind == "pull_request",
                    IssueVcsLink.pr_url == pr_url,
                )
            )
            row = result.scalar_one_or_none()
            if row:
                return row
        if external_id:
            result = await self.db.execute(
                select(IssueVcsLink).where(
                    IssueVcsLink.kind == "pull_request",
                    IssueVcsLink.external_id == str(external_id),
                    IssueVcsLink.provider == "github",
                )
            )
            return result.scalar_one_or_none()
        return None

    async def upsert_github_pr(
        self,
        *,
        pr_url: str,
        external_id: str | None,
        status: str,
        title: str | None,
        head_ref: str | None,
    ) -> IssueVcsLink:
        from opentask.services.vcs.branch_naming import parse_issue_code_from_branch

        issue: Issue | None = None
        existing = await self.find_link_by_pr(pr_url=pr_url, external_id=external_id)

        if head_ref:
            code = parse_issue_code_from_branch(head_ref)
            if code:
                issue = await self.find_issue_by_code(code)

        if existing:
            if not issue:
                issue = await self.get_issue(
                    workspace_id=existing.workspace_id, issue_id=existing.issue_id
                )
            existing.status = status
            existing.title = title or existing.title
            existing.branch_name = head_ref or existing.branch_name
            if external_id:
                existing.external_id = str(external_id)
            if pr_url:
                existing.pr_url = pr_url
            existing.provider = "github"
            existing.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        if not issue:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="无法从分支名解析 Issue，且无已有 PR 关联",
            )

        return await self.create_link(
            workspace_id=issue.workspace_id,
            issue_id=issue.id,
            user_id="github-webhook",
            kind="pull_request",
            branch_name=head_ref,
            pr_url=pr_url,
            provider="github",
            external_id=str(external_id) if external_id is not None else None,
            status=status,
            title=title,
        )
