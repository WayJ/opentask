from datetime import datetime
from typing import TYPE_CHECKING

from opentask.models.base import DBModel, UUIDMixin
from opentask.models.conversation.enums import ConversationType
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from opentask.models.message.model import MessageModel


class ConversationModel(DBModel, UUIDMixin, kw_only=True):
    __tablename__ = "conversations"
    name: Mapped[str] = mapped_column("name", String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=False)

    # 对话类型字段（存储为字符串，使用 ConversationType 枚举进行类型安全）
    conversation_type: Mapped[str] = mapped_column(
        "conversation_type",
        String(50),
        nullable=False,
        insert_default=ConversationType.SQL_CHAT.value
    )
    workspace_id: Mapped[str] = mapped_column("workspace_id", Text, nullable=True)
    ai_settings: Mapped[str] = mapped_column("ai_settings", Text, nullable=True)  # JSON string

    # Relationships
    messages: Mapped[list["MessageModel"]] = relationship("MessageModel", back_populates="conversation")

    def get_conversation_type_enum(self) -> ConversationType:
        """获取对话类型的枚举值"""
        return ConversationType.from_string(self.conversation_type)
