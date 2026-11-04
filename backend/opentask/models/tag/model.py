"""Tag / TagGroup models（E7-S1：Workspace 作用域 Labels）"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from opentask.models.base import DBModel


def _uuid() -> str:
    return str(uuid.uuid4())


class TagGroup(DBModel, kw_only=True):
    """工作区内标签分组"""

    __tablename__ = "tag_groups"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, insert_default=_uuid)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, insert_default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    tags: Mapped[list["Tag"]] = relationship("Tag", back_populates="group")

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_tag_groups_ws_name"),
    )


class Tag(DBModel, kw_only=True):
    """工作区标签（Labels）"""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    workspace_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    color: Mapped[str] = mapped_column(
        String(20), nullable=False, insert_default="#3b82f6", server_default="#3b82f6"
    )
    group_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("tag_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, insert_default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, insert_default=datetime.utcnow, onupdate=datetime.utcnow
    )

    group: Mapped[Optional["TagGroup"]] = relationship("TagGroup", back_populates="tags")

    __table_args__ = (
        UniqueConstraint("workspace_id", "name", name="uq_tags_ws_name"),
    )
