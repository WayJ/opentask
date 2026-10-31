from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from typing_extensions import Self

from opentask.models.conversation.enums import ConversationType


class ConversationsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    conversations: list["ConversationOut"]


class CreateConversationIn(BaseModel):
    name: str
    conversation_type: ConversationType = Field(
        default=ConversationType.SQL_CHAT,
        description="对话类型"
    )
    ai_settings: Optional[dict] = Field(default=None, description="AI设置")

    def __init__(self, **data):
        # 处理字符串类型的 conversation_type
        if 'conversation_type' in data and isinstance(data['conversation_type'], str):
            data['conversation_type'] = ConversationType.from_string(data['conversation_type'])
        super().__init__(**data)


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    created_at: datetime
    conversation_type: ConversationType = Field(
        default=ConversationType.SQL_CHAT,
        description="对话类型"
    )
    workspace_id: Optional[str] = Field(default=None, description="工作空间ID")
    ai_settings: Optional[dict] = Field(default=None, description="AI设置")


class UpdateConversationRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="对话名称")
    ai_settings: Optional[dict] = Field(default=None, description="AI设置")
