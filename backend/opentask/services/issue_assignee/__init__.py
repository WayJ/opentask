"""E71: multi-assignee helpers."""
from opentask.services.issue_assignee.service import (
    MAX_ISSUE_ASSIGNEES,
    normalize_assignee_ids,
)

__all__ = ["MAX_ISSUE_ASSIGNEES", "normalize_assignee_ids"]
