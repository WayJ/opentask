"""Issue VCS API (E11-S1) — branch-name + links; not Requirement/PGE."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.issue_vcs_link.model import VCS_LINK_KINDS
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.vcs.service import IssueVcsService, require_writer, serialize_vcs_link
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/issues", tags=["Issue VCS"])


class VcsLinkCreate(BaseModel):
    kind: str
    branchName: Optional[str] = Field(None, max_length=255)
    prUrl: Optional[str] = Field(None, max_length=500)
    provider: str = "manual"
    externalId: Optional[str] = Field(None, max_length=100)
    status: str = "unknown"
    title: Optional[str] = Field(None, max_length=255)
    repoConfigId: Optional[int] = None

    @field_validator("kind")
    @classmethod
    def _kind(cls, v: str) -> str:
        if v not in VCS_LINK_KINDS:
            raise ValueError(f"kind must be one of {VCS_LINK_KINDS}")
        return v


@router.get("/{issue_id}/vcs/branch-name")
async def get_branch_name(
    issue_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    data = await IssueVcsService(session).branch_name(
        workspace_id=ws.id, issue_id=issue_id
    )
    return success_response(data=data)


@router.get("/{issue_id}/vcs/links")
async def list_links(
    issue_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows = await IssueVcsService(session).list_links(
        workspace_id=ws.id, issue_id=issue_id
    )
    return success_response(
        data={"rows": [serialize_vcs_link(r) for r in rows], "total": len(rows)}
    )


@router.post("/{issue_id}/vcs/links")
async def create_link(
    issue_id: str,
    body: VcsLinkCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    row = await IssueVcsService(session).create_link(
        workspace_id=ws.id,
        issue_id=issue_id,
        user_id=str(user.id),
        kind=body.kind,
        branch_name=body.branchName,
        pr_url=body.prUrl,
        provider=body.provider,
        external_id=body.externalId,
        status=body.status,
        title=body.title,
        repo_config_id=body.repoConfigId,
    )
    return success_response(data=serialize_vcs_link(row), message="已关联")


@router.delete("/{issue_id}/vcs/links/{link_id}")
async def delete_link(
    issue_id: str,
    link_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    await IssueVcsService(session).delete_link(
        workspace_id=ws.id, issue_id=issue_id, link_id=link_id
    )
    return success_response(data={"id": link_id}, message="已解除关联")
