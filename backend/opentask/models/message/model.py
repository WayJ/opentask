from datetime import datetime
from typing import Any
from uuid import UUID

from opentask.models.base import DBModel, UUIDMixin
from opentask.models.conversation.model import ConversationModel
from sqlalchemy import JSON, ForeignKey, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship


class MessageModel(DBModel, UUIDMixin, kw_only=True):  # type: ignore[misc]
    __tablename__ = "messages"
    content: Mapped[str] = mapped_column("content", Text, nullable=False)
    role: Mapped[str] = mapped_column("role", String(50), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime, insert_default=datetime.utcnow, nullable=True)
    conversation_id: Mapped[UUID] = mapped_column(ForeignKey(ConversationModel.id, ondelete="CASCADE"))
    options: Mapped[dict[str, Any] | None] = mapped_column("options", JSON, nullable=True)  # type: ignore[misc]

    # Relationships
    conversation: Mapped[ConversationModel] = relationship("ConversationModel", back_populates="messages")
