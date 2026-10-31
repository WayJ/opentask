from typing import Sequence, Type
from uuid import UUID

from sqlalchemy import select

from opentask.models.message.model import MessageModel
from opentask.models.message.schema import MessageCreate, MessageUpdate
from opentask.repositories.base import AsyncSession, BaseRepository


class MessageRepository(BaseRepository[MessageModel, MessageCreate, MessageUpdate]):
    @property
    def model(self) -> Type[MessageModel]:
        return MessageModel

    async def get_by_conversation(self, session: AsyncSession, conversation_id: UUID) -> Sequence[MessageModel]:
        query = select(MessageModel).filter_by(conversation_id=conversation_id).order_by(MessageModel.created_at)
        return await self.list(session, query=query)
