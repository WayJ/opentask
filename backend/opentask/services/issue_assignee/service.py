"""E71: issue multi-assignee service — normalize, validate, replace."""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.models.issue.model import Issue
from opentask.models.issue_assignee.model import IssueAssignee
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import WorkspaceMember

MAX_ISSUE_ASSIGNEES = 10


def normalize_assignee_ids(ids: Optional[Iterable[str | None]]) -> list[str]:
    """Order-preserving dedupe; empty/None stripped; raises if > max."""
    if not ids:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in ids:
        if raw is None:
            continue
        uid = str(raw).strip()
        if not uid or uid in seen:
            continue
        seen.add(uid)
        out.append(uid)
    if len(out) > MAX_ISSUE_ASSIGNEES:
        raise ValueError(f"max {MAX_ISSUE_ASSIGNEES} assignees")
    return out


async def list_assignee_ids(db: AsyncSession, issue_id: str) -> list[str]:
    q = await db.execute(
        select(IssueAssignee.user_id)
        .where(IssueAssignee.issue_id == issue_id)
        .order_by(IssueAssignee.position.asc(), IssueAssignee.created_at.asc())
    )
    return [str(uid) for uid in q.scalars().all()]


async def validate_assignee_members(
    db: AsyncSession, workspace_id: str, user_ids: list[str]
) -> None:
    if not user_ids:
        return
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="workspace required for assignees",
        )
    q = await db.execute(
        select(WorkspaceMember.user_id).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id.in_(user_ids),
        )
    )
    found = {str(uid) for uid in q.scalars().all()}
    missing = [uid for uid in user_ids if uid not in found]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="assignee must be workspace member",
        )


async def replace_issue_assignees(
    db: AsyncSession,
    *,
    issue: Issue,
    user_ids: list[str],
    validate: bool = True,
) -> list[str]:
    """Replace junction rows; mirror issue.assignee_id = first or None. Caller commits."""
    try:
        ids = normalize_assignee_ids(user_ids)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        ) from e

    if validate:
        await validate_assignee_members(db, issue.workspace_id, ids)

    await db.execute(
        delete(IssueAssignee).where(IssueAssignee.issue_id == issue.id)
    )
    now = datetime.utcnow()
    for pos, uid in enumerate(ids):
        db.add(
            IssueAssignee(
                id=str(uuid4()),
                workspace_id=issue.workspace_id,
                issue_id=issue.id,
                user_id=uid,
                position=pos,
                created_at=now,
            )
        )
    issue.assignee_id = ids[0] if ids else None
    await db.flush()
    return ids


def _user_info_dict(u: UserModel | None, user_id: str) -> dict:
    if u is None:
        return {"id": user_id, "name": None, "sso_name": None, "sso_account": None}
    return {
        "id": str(u.id),
        "name": getattr(u, "name", None),
        "sso_name": getattr(u, "sso_name", None),
        "sso_account": getattr(u, "sso_account", None),
    }


async def list_assignee_user_infos(
    db: AsyncSession, issue_id: str
) -> list[dict]:
    ids = await list_assignee_ids(db, issue_id)
    if not ids:
        return []
    q = await db.execute(select(UserModel).where(UserModel.id.in_(ids)))
    users = {str(u.id): u for u in q.scalars().all()}
    return [_user_info_dict(users.get(uid), uid) for uid in ids]


async def list_assignee_user_infos_for_issues(
    db: AsyncSession, issue_ids: list[str]
) -> dict[str, list[dict]]:
    if not issue_ids:
        return {}
    q = await db.execute(
        select(IssueAssignee)
        .where(IssueAssignee.issue_id.in_(issue_ids))
        .order_by(IssueAssignee.position.asc(), IssueAssignee.created_at.asc())
    )
    rows = list(q.scalars().all())
    user_ids = list({str(r.user_id) for r in rows})
    users: dict[str, UserModel] = {}
    if user_ids:
        uq = await db.execute(select(UserModel).where(UserModel.id.in_(user_ids)))
        users = {str(u.id): u for u in uq.scalars().all()}
    out: dict[str, list[dict]] = {iid: [] for iid in issue_ids}
    for r in rows:
        out.setdefault(str(r.issue_id), []).append(
            _user_info_dict(users.get(str(r.user_id)), str(r.user_id))
        )
    return out
