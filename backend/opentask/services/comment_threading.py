"""E74: comment threading helpers — depth=1 parent validation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException


@dataclass(frozen=True)
class ParentCommentView:
    id: str
    issue_id: str
    parent_id: Optional[str]
    is_deleted: bool
    user_id: Optional[str] = None


def validate_comment_parent(
    *,
    issue_id: str,
    parent: Optional[ParentCommentView],
    parent_id: Optional[str],
) -> None:
    """Validate parent for depth=1 threading. Raise HTTPException(400) on failure."""
    if not parent_id:
        return
    if parent is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "parent_not_found",
                "message": "parent comment not found",
            },
        )
    if str(parent.issue_id) != str(issue_id):
        raise HTTPException(
            status_code=400,
            detail={
                "code": "parent_cross_issue",
                "message": "parent comment belongs to a different issue",
            },
        )
    if parent.is_deleted:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "parent_deleted",
                "message": "parent comment is deleted",
            },
        )
    if parent.parent_id is not None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "parent_not_root",
                "message": "replies may only target root comments (depth=1)",
            },
        )
