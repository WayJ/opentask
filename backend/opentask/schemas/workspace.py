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
    createdAt: datetime
    updatedAt: datetime
