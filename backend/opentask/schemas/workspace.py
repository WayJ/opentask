"""Workspace API schemas"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    slug: Optional[str] = Field(None, min_length=1, max_length=80)
    description: Optional[str] = None


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    description: Optional[str] = None
    cyclesEnabled: Optional[bool] = None
    cycleDurationDays: Optional[int] = Field(None, ge=1, le=365)
    cycleRolloverPolicy: Optional[str] = Field(None, pattern="^(into_next|leave_unassigned)$")
    cycleCapacityLookback: Optional[int] = Field(None, ge=1, le=20)
    issueKey: Optional[str] = Field(None, min_length=1, max_length=6)


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
    createdAt: datetime
    updatedAt: datetime
