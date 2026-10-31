"""Tag Model

最小化实现，用于解决 IssueTag 的外键引用问题。
"""

from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from opentask.models.base import DBModel


class Tag(DBModel, kw_only=True):
    """标签模型"""
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=False)
