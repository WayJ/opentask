"""Optional PR → Issue status hooks (E11-S3). Default off at Workspace."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.enums import IssueStatus
from opentask.models.issue.model import Issue
from opentask.models.issue.schema import IssueUpdate
from opentask.models.workspace.model import Workspace
from opentask.services.issue_service import IssueService


def should_apply_open_hook(current_status: str) -> bool:
    """Only advance from open; never disturb in_progress/feedback/etc."""
    return (current_status or "").lower() == IssueStatus.OPEN.value


def should_apply_merged_hook(current_status: str) -> bool:
    """Do not touch closed/rejected."""
    st = (current_status or "").lower()
    return st not in {IssueStatus.CLOSED.value, IssueStatus.REJECTED.value}


async def apply_pr_status_hooks(
    db: AsyncSession,
    *,
    workspace_id: str,
    issue_id: str,
    pr_link_status: str,
) -> Optional[str]:
    """Apply Issue status change when WS hooks enabled.

    Returns new status string if changed, else None.
    """
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    ws = result.scalar_one_or_none()
    if ws is None or not bool(getattr(ws, "git_status_hooks_enabled", False)):
        return None

    issue_result = await db.execute(
        select(Issue).where(Issue.id == issue_id, Issue.is_deleted == False)  # noqa: E712
    )
    issue = issue_result.scalar_one_or_none()
    if issue is None:
        return None

    current = issue.status.value if hasattr(issue.status, "value") else str(issue.status)
    pr_st = (pr_link_status or "").lower()
    target: Optional[str] = None

    if pr_st == "merged":
        if should_apply_merged_hook(current):
            target = getattr(ws, "git_hook_on_pr_merged", None) or IssueStatus.RESOLVED.value
    elif pr_st in {"open", "draft"}:
        if should_apply_open_hook(current):
            target = getattr(ws, "git_hook_on_pr_open", None) or IssueStatus.IN_PROGRESS.value
    else:
        # closed (unmerged) and others: no-op
        return None

    if not target or target == current:
        return None

    await IssueService(db).update_issue(
        issue_id=issue_id,
        data=IssueUpdate(status=IssueStatus(target)),
        user_id="github-webhook",
    )
    return target
