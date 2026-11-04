"""Workspace 实时事件类型常量。"""

from __future__ import annotations

ISSUE_CREATED = "issue.created"
ISSUE_UPDATED = "issue.updated"
ISSUE_DELETED = "issue.deleted"
INBOX_CREATED = "inbox.created"
COMMENT_CREATED = "comment.created"

ALL_TYPES = frozenset(
    {
        ISSUE_CREATED,
        ISSUE_UPDATED,
        ISSUE_DELETED,
        INBOX_CREATED,
        COMMENT_CREATED,
    }
)
