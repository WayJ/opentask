from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from opentask.models.conversation.schema import ConversationOut


class BaseMessageType(Enum):
    AI = "ai"
    HUMAN = "human"
    SYSTEM = "system"


class MessageOptions(BaseModel):
    secure_data: bool = True


class MessageCreate(BaseModel):
    created_at: datetime = Field(default_factory=datetime.now)

    content: str
    role: str
    conversation_id: UUID

    options: Optional[MessageOptions] = None


class MessageUpdate(BaseModel):
    content: str
    role: str
    conversation_id: UUID


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content: str
    role: Literal["ai"] | Literal["human"]
    created_at: datetime

    options: Optional[MessageOptions]


class MessageWithResultsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: MessageOut
    results: list = []  # 简化：不再使用 ResultOut


class QueryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    human_message: MessageOut
    ai_message: MessageOut  # 简化：不再使用 MessageWithResultsOut


# ConversationWithMessagesOut 移到这里避免循环导入
class ConversationWithMessagesOut(BaseModel):
    """带消息的对话输出模型"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    created_at: datetime
    conversation_type: str  # ConversationType
    workspace_id: Optional[str] = None
    ai_settings: Optional[dict] = None
    messages: list[MessageOut]
