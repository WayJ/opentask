"""Inbox / Notification API schemas"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NotificationOut(BaseModel):
    id: str
    workspaceId: str
    recipientUserId: str
    actorUserId: Optional[str] = None
    type: str
    resourceType: str
    resourceId: str
    title: str
    body: Optional[str] = None
    readAt: Optional[datetime] = None
    createdAt: datetime


class InboxListOut(BaseModel):
    rows: list[NotificationOut]
    total: int
    page: int
    pageSize: int
    unreadCount: int
