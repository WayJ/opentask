import logging
from typing import AsyncGenerator
from uuid import UUID

from fastapi import Depends
from openai._exceptions import APIError

from opentask.errors import UserFacingError
from opentask.models.conversation.enums import ConversationType
from opentask.models.conversation.schema import (
    ConversationOut,
    CreateConversationIn,
)
from opentask.models.message.schema import ConversationWithMessagesOut
from opentask.models.message.schema import (
    BaseMessageType,
    MessageCreate,
    MessageOptions,
    MessageOut,
)
from opentask.repositories.base import AsyncSession
from opentask.repositories.conversation import (
    ConversationRepository,
    ConversationUpdate,
)
from opentask.repositories.message import MessageRepository
from opentask.services.settings import SettingsService

logger = logging.getLogger(__name__)


class ConversationService:
    conversation_repo: ConversationRepository
    message_repo: MessageRepository
    settings_service: SettingsService

    def __init__(
        self,
        conversation_repo: ConversationRepository = Depends(ConversationRepository),
        message_repo: MessageRepository = Depends(MessageRepository),
        settings_service: SettingsService = Depends(SettingsService),
    ) -> None:
        self.conversation_repo = conversation_repo
        self.message_repo = message_repo
        self.settings_service = settings_service

    async def generate_title(self, session: AsyncSession, conversation_id: UUID) -> str:
        """生成对话标题（简化版本，使用第一条消息的前50个字符）"""
        conversation = await self.get_conversation_with_messages(session, conversation_id)
        if not conversation.messages:
            return "Untitled chat"

        first_message_content = conversation.messages[0].content

        # 使用第一条消息的前50个字符作为标题
        title = first_message_content[:50] + "..." if len(first_message_content) > 50 else first_message_content

        # 更新对话标题
        await self.update_conversation_name(session, conversation_id, title)

        return title

    async def create_conversation(
        self,
        session: AsyncSession,
        user_id: str,
        data: CreateConversationIn,
    ) -> ConversationOut:
        """创建新对话"""
        from opentask.models.conversation.model import ConversationModel

        conversation = ConversationModel(
            name=data.name,
            conversation_type=data.conversation_type,
            ai_settings=data.ai_settings,
            workspace_id=None,
        )
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)

        # 处理 ai_settings 字段转换
        ai_settings_dict = None
        if conversation.ai_settings:
            try:
                import json
                ai_settings_dict = json.loads(conversation.ai_settings)
            except (json.JSONDecodeError, TypeError):
                ai_settings_dict = None

        return ConversationOut(
            id=str(conversation.id),
            name=conversation.name,
            created_at=conversation.created_at,
            conversation_type=conversation.conversation_type,
            workspace_id=conversation.workspace_id,
            ai_settings=ai_settings_dict
        )

    async def get_conversation(self, session: AsyncSession, conversation_id: UUID) -> ConversationOut | None:
        """获取单个对话"""
        from opentask.models.conversation.model import ConversationModel

        from sqlalchemy import select

        result = await session.execute(select(ConversationModel).filter_by(id=conversation_id))
        conversation = result.scalar_one_or_none()

        if not conversation:
            return None

        # 处理 ai_settings 字段转换
        ai_settings_dict = None
        if conversation.ai_settings:
            try:
                import json
                ai_settings_dict = json.loads(conversation.ai_settings)
            except (json.JSONDecodeError, TypeError):
                ai_settings_dict = None

        return ConversationOut(
            id=str(conversation.id),
            name=conversation.name,
            created_at=conversation.created_at,
            conversation_type=conversation.conversation_type,
            workspace_id=conversation.workspace_id,
            ai_settings=ai_settings_dict
        )

    async def list_conversations(
        self, session: AsyncSession, user_id: str
    ) -> list[ConversationOut]:
        """列出所有对话"""
        from opentask.models.conversation.model import ConversationModel

        from sqlalchemy import select

        result = await session.execute(
            select(ConversationModel)
            .order_by(ConversationModel.created_at.desc())
        )
        conversations = result.scalars().all()

        output = []
        for conversation in conversations:
            # 处理 ai_settings 字段转换
            ai_settings_dict = None
            if conversation.ai_settings:
                try:
                    import json
                    ai_settings_dict = json.loads(conversation.ai_settings)
                except (json.JSONDecodeError, TypeError):
                    ai_settings_dict = None

            output.append(ConversationOut(
                id=str(conversation.id),
                name=conversation.name,
                created_at=conversation.created_at,
                conversation_type=conversation.conversation_type,
                workspace_id=conversation.workspace_id,
                ai_settings=ai_settings_dict
            ))

        return output

    async def get_conversation_with_messages(
        self, session: AsyncSession, conversation_id: UUID
    ) -> ConversationWithMessagesOut | None:
        """获取对话及其消息"""
        from opentask.models.conversation.model import ConversationModel
        from opentask.models.message.schema import MessageOut

        from sqlalchemy import select

        result = await session.execute(
            select(ConversationModel)
            .filter_by(id=conversation_id)
        )
        conversation = result.scalar_one_or_none()

        if not conversation:
            return None

        # 获取消息
        messages = await self.message_repo.get_by_conversation(session, conversation_id)
        message_outs = [MessageOut.model_validate(msg) for msg in messages]

        # 处理 ai_settings 字段转换
        ai_settings_dict = None
        if conversation.ai_settings:
            try:
                import json
                ai_settings_dict = json.loads(conversation.ai_settings)
            except (json.JSONDecodeError, TypeError):
                ai_settings_dict = None

        return ConversationWithMessagesOut(
            id=str(conversation.id),
            name=conversation.name,
            created_at=conversation.created_at,
            conversation_type=conversation.conversation_type,
            workspace_id=conversation.workspace_id,
            ai_settings=ai_settings_dict,
            messages=message_outs,
        )

    async def delete_conversation(
        self, session: AsyncSession, conversation_id: UUID
    ) -> bool:
        """删除对话"""
        from opentask.models.conversation.model import ConversationModel

        from sqlalchemy import select, delete

        result = await session.execute(
            delete(ConversationModel).filter_by(id=conversation_id).returning(ConversationModel.id)
        )
        await session.commit()

        return result.scalar_one_or_none() is not None

    async def update_conversation(
        self, session: AsyncSession, conversation_id: UUID, data: CreateConversationIn
    ) -> ConversationOut | None:
        """更新对话"""
        from opentask.models.conversation.model import ConversationModel

        from sqlalchemy import select

        result = await session.execute(select(ConversationModel).filter_by(id=conversation_id))
        conversation = result.scalar_one_or_none()

        if not conversation:
            return None

        if data.name is not None:
            conversation.name = data.name
        if data.ai_settings is not None:
            conversation.ai_settings = data.ai_settings

        await session.commit()
        await session.refresh(conversation)

        # 处理 ai_settings 字段转换
        ai_settings_dict = None
        if conversation.ai_settings:
            try:
                import json
                ai_settings_dict = json.loads(conversation.ai_settings)
            except (json.JSONDecodeError, TypeError):
                ai_settings_dict = None

        return ConversationOut(
            id=str(conversation.id),
            name=conversation.name,
            created_at=conversation.created_at,
            conversation_type=conversation.conversation_type,
            workspace_id=conversation.workspace_id,
            ai_settings=ai_settings_dict
        )

    async def update_conversation_name(
        self, session: AsyncSession, conversation_id: UUID, name: str
    ) -> ConversationOut:
        """更新对话名称"""
        conversation = await self.conversation_repo.update_by_uuid(
            session, conversation_id, ConversationUpdate(name=name)
        )
        return ConversationOut.model_validate(conversation)

    async def query(
        self,
        session: AsyncSession,
        conversation_id: UUID,
        query: str,
        secure_data: bool = True,
    ) -> AsyncGenerator[str, None]:
        """
        处理对话查询
        仅支持 NORMAL_CHAT 类型（使用 Agent v3）
        """
        # Get conversation first to check type
        conversation = await self.get_conversation(session, conversation_id=conversation_id)

        if not conversation:
            raise UserFacingError("对话不存在")

        # 仅支持普通对话类型，使用 Agent v3
        if conversation.conversation_type != ConversationType.NORMAL_CHAT:
            raise UserFacingError(f"不支持的对话类型: {conversation.conversation_type.value}")

        # 使用 Agent v3 处理查询
        from opentask.services.agent_v3.integration import AgentV3Service

        agent_v3_service = AgentV3Service(
            message_repo=self.message_repo,
            settings_service=self.settings_service
        )

        async for event in agent_v3_service.query(
            session=session,
            conversation_id=conversation_id,
            query=query
        ):
            yield event
