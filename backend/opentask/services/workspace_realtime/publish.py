"""Best-effort publish helpers — 永不抛到写路径。"""

from __future__ import annotations

import logging
from typing import Any, Optional

from opentask.services.workspace_realtime import events
from opentask.services.workspace_realtime.hub import get_workspace_realtime_hub

logger = logging.getLogger(__name__)


async def _safe_publish(
    workspace_id: Optional[str],
    event_type: str,
    payload: dict[str, Any],
    *,
    actor_user_id: Optional[str] = None,
    skip_actor: bool = True,
) -> None:
    if not workspace_id:
        return
    try:
        hub = get_workspace_realtime_hub()
        await hub.publish(
            workspace_id,
            event_type,
            payload,
            actor_user_id=actor_user_id,
            skip_actor=skip_actor,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "workspace realtime publish failed type=%s ws=%s",
            event_type,
            workspace_id,
        )


async def publish_issue_created(issue: Any, *, actor_user_id: Optional[str] = None) -> None:
    await _safe_publish(
        getattr(issue, "workspace_id", None),
        events.ISSUE_CREATED,
        {
            "id": str(getattr(issue, "id", "")),
            "issue_code": getattr(issue, "issue_code", None),
            "title": getattr(issue, "title", None),
            "status": _enum_val(getattr(issue, "status", None)),
        },
        actor_user_id=actor_user_id,
    )


async def publish_issue_updated(
    issue: Any,
    *,
    actor_user_id: Optional[str] = None,
    changed: Optional[list[str]] = None,
) -> None:
    await _safe_publish(
        getattr(issue, "workspace_id", None),
        events.ISSUE_UPDATED,
        {
            "id": str(getattr(issue, "id", "")),
            "issue_code": getattr(issue, "issue_code", None),
            "changed": list(changed or []),
            "status": _enum_val(getattr(issue, "status", None)),
            "title": getattr(issue, "title", None),
        },
        actor_user_id=actor_user_id,
    )


async def publish_issue_deleted(
    issue: Any,
    *,
    actor_user_id: Optional[str] = None,
) -> None:
    await _safe_publish(
        getattr(issue, "workspace_id", None),
        events.ISSUE_DELETED,
        {
            "id": str(getattr(issue, "id", "")),
            "issue_code": getattr(issue, "issue_code", None),
        },
        actor_user_id=actor_user_id,
    )


async def publish_inbox_created(
    notification: Any,
    *,
    actor_user_id: Optional[str] = None,
) -> None:
    await _safe_publish(
        getattr(notification, "workspace_id", None),
        events.INBOX_CREATED,
        {
            "id": str(getattr(notification, "id", "")),
            "recipient_user_id": str(getattr(notification, "recipient_user_id", "")),
            "notification_type": getattr(notification, "type", None),
            "resource_type": getattr(notification, "resource_type", None),
            "resource_id": getattr(notification, "resource_id", None),
            "title": getattr(notification, "title", None),
        },
        actor_user_id=actor_user_id,
        # 通知对 actor 也无意义；仍 skip actor
        skip_actor=True,
    )


async def publish_comment_created(
    *,
    workspace_id: Optional[str],
    issue_id: str,
    comment_id: str,
    issue_code: Optional[str] = None,
    actor_user_id: Optional[str] = None,
) -> None:
    await _safe_publish(
        workspace_id,
        events.COMMENT_CREATED,
        {
            "id": str(comment_id),
            "issue_id": str(issue_id),
            "issue_code": issue_code,
        },
        actor_user_id=actor_user_id,
    )


def _enum_val(v: Any) -> Any:
    return getattr(v, "value", v)
