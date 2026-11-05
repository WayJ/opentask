"""E66/E69: attachment read ACL — session user must be a member of the Issue's workspace.

E69: also resolves entity_type=issue_comment → parent Issue → WS membership.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.document.model import Document
from opentask.services.workspace.service import WorkspaceService


async def require_attachment_read(
    session: AsyncSession,
    *,
    user_id: str,
    attachment_id: str,
    issue_service,
) -> Document:
    """Resolve attachment and enforce workspace membership.

    Missing attachment / orphan issue / non-member → 404 (tenant-uniform, D3).
    Supports entity_type in {issue, issue_comment}.
    """
    attachment = await issue_service.get_attachment_by_id(attachment_id)
    if attachment is None:
        raise HTTPException(status_code=404, detail="附件不存在")

    if attachment.entity_type == "issue":
        issue = await issue_service.get_issue(attachment.entity_id)
    elif attachment.entity_type == "issue_comment":
        comment = await issue_service.get_comment_by_id(
            attachment.entity_id, include_deleted=True
        )
        if comment is None:
            raise HTTPException(status_code=404, detail="附件不存在")
        issue = await issue_service.get_issue(comment.issue_id)
    else:
        raise HTTPException(status_code=404, detail="附件不存在")

    if issue is None:
        raise HTTPException(status_code=404, detail="附件不存在")

    if issue.workspace_id:
        member = await WorkspaceService(session).get_membership(
            issue.workspace_id, user_id
        )
        if member is None:
            raise HTTPException(status_code=404, detail="附件不存在")

    return attachment
