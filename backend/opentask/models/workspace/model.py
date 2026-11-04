"""Workspace 租户模型（E3-S1）"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel


def _uuid() -> str:
    return str(uuid.uuid4())


class Workspace(DBModel):
    """工作区（租户根）"""

    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    name: Mapped[str] = mapped_column(String(120), nullable=False, comment="显示名")
    slug: Mapped[str] = mapped_column(String(80), nullable=False, comment="URL/唯一短名")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cycles_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, insert_default=False, server_default="false", comment="启用 Cycles"
    )
    cycle_duration_days: Mapped[int] = mapped_column(
        Integer, nullable=False, insert_default=14, server_default="14", comment="默认 Cycle 天数"
    )
    cycle_rollover_policy: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        insert_default="into_next",
        server_default="into_next",
        comment="into_next|leave_unassigned",
    )
    cycle_capacity_lookback: Mapped[int] = mapped_column(
        Integer, nullable=False, insert_default=3, server_default="3", comment="容量回看 completed Cycle 数"
    )
    issue_key: Mapped[str] = mapped_column(
        String(6),
        nullable=False,
        insert_default="OT",
        server_default="OT",
        comment="Issue 单号前缀 KEY（2–6 大写字母数字）",
    )
    issue_counter: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        insert_default=0,
        server_default="0",
        comment="已分配最大序号；下一单 = counter+1",
    )
    git_status_hooks_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        insert_default=False,
        server_default="false",
        comment="PR webhook 可自动更新 Issue 状态",
    )
    git_hook_on_pr_open: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        insert_default="in_progress",
        server_default="in_progress",
        comment="PR open/draft 目标 Issue 状态",
    )
    git_hook_on_pr_merged: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        insert_default="resolved",
        server_default="resolved",
        comment="PR merged 目标 Issue 状态",
    )

    timezone: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        comment="IANA timezone for SLA business hours",
    )
    business_hours: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"),
        nullable=True,
        comment="E50: {enabled, windows{mon..sun:[{start,end}]}}",
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("slug", name="uq_workspaces_slug"),
        UniqueConstraint("issue_key", name="uq_workspaces_issue_key"),
        Index("idx_workspaces_created_by", "created_by"),
    )


class WorkspaceMember(DBModel):
    """工作区成员"""

    __tablename__ = "workspace_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, insert_default="member", comment="owner|member|viewer"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_members_ws_user"),
        Index("idx_workspace_members_user", "user_id"),
    )
