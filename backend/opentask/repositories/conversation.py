from datetime import datetime
from typing import Sequence, Type, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from opentask.models.conversation.model import ConversationModel
from opentask.models.message.model import MessageModel
from opentask.repositories.base import AsyncSession, BaseRepository


class ConversationCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")
    name: str
    conversation_type: str = Field(default="sql_chat", description="对话类型")
    ai_settings: str | None = Field(default=None, description="AI设置-JSON字符串")
    created_at: datetime = Field(default_factory=datetime.now)
    connection_id: Optional[UUID] = None

class ConversationUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    connection_id: Optional[UUID] = None
    name: str | None = None


class ConversationRepository(BaseRepository[ConversationModel, ConversationCreate, ConversationUpdate]):
    @property
    def model(self) -> Type[ConversationModel]:
        return ConversationModel

    async def get_with_messages_with_results(self, session: AsyncSession, conversation_id: UUID) -> ConversationModel:
        query = (
            select(ConversationModel)
            .filter_by(id=conversation_id)
            .options(joinedload(ConversationModel.messages).joinedload(MessageModel.results))
        )
        return await self.get_unique(session, query)

    async def list_with_messages_with_results(self, session: AsyncSession) -> Sequence[ConversationModel]:
        query = select(ConversationModel).options(
            joinedload(ConversationModel.messages).joinedload(MessageModel.results)
        )
        return await self.list_unique(session, query)
