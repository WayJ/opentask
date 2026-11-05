"""Workspace API schemas"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    slug: Optional[str] = Field(None, min_length=1, max_length=80)
    description: Optional[str] = None
    issueKey: Optional[str] = Field(None, min_length=1, max_length=6)


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = None
    cyclesEnabled: Optional[bool] = None
    cycleDurationDays: Optional[int] = Field(None, ge=1, le=365)
    cycleRolloverPolicy: Optional[str] = Field(None, pattern="^(into_next|leave_unassigned)$")
    cycleCapacityLookback: Optional[int] = Field(None, ge=1, le=20)
    issueKey: Optional[str] = Field(None, min_length=1, max_length=6)
    gitStatusHooksEnabled: Optional[bool] = None
    gitHookOnPrOpen: Optional[str] = Field(None, max_length=32)
    gitHookOnPrMerged: Optional[str] = Field(None, max_length=32)
    timezone: Optional[str] = Field(None, max_length=64)
    businessHours: Optional[dict[str, Any]] = None


class WorkspaceMemberAdd(BaseModel):
    userId: str = Field(..., min_length=1)
    role: str = Field(default="member", pattern="^(owner|member|viewer)$")


class WorkspaceMemberOut(BaseModel):
    id: str
    userId: str
    role: str
    createdAt: datetime


class WorkspaceOut(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    role: Optional[str] = None  # 当前用户在该工作区的角色
    cyclesEnabled: bool = False
    cycleDurationDays: int = 14
    cycleRolloverPolicy: str = "into_next"
    cycleCapacityLookback: int = 3
    issueKey: str = "OT"
    gitStatusHooksEnabled: bool = False
    gitHookOnPrOpen: str = "in_progress"
    gitHookOnPrMerged: str = "resolved"
    timezone: Optional[str] = None
    businessHours: Optional[dict[str, Any]] = None
    createdAt: datetime
    updatedAt: datetime


class WorkspaceMemberRoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(owner|member|viewer)$")


class WorkspaceInviteCreate(BaseModel):
    email: Optional[str] = Field(None, max_length=255)
    role: str = Field(default="member", pattern="^(member|viewer)$")
    expiresInDays: Optional[int] = Field(14, ge=1, le=90)
