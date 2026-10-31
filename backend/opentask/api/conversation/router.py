import logging
from typing import Optional
from typing_extensions import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from opentask.models.conversation.schema import (
    ConversationOut,
    CreateConversationIn,
    UpdateConversationRequest,
)
from opentask.models.message.schema import ConversationWithMessagesOut
from opentask.models.common.response import SuccessResponse
from opentask.repositories.base import AsyncSession, get_session
from opentask.services.conversation import ConversationService
from opentask.auth import authenticate
from opentask.models.user.model import UserModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


@router.get("/conversation/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
    conversation_service: ConversationService = Depends(),
) -> SuccessResponse[ConversationOut]:
    conversation = await conversation_service.get_conversation(session, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return SuccessResponse(data=conversation)


@router.get("")
async def conversations(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(authenticate),
    conversation_service: ConversationService = Depends(),
) -> SuccessResponse[list[ConversationOut]]:
    conversations_list = await conversation_service.list_conversations(session, str(current_user.id))
    return SuccessResponse(data=conversations_list)


@router.get("/conversation/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
    conversation_service: ConversationService = Depends(),
) -> SuccessResponse[ConversationWithMessagesOut]:
    conversation_with_messages = await conversation_service.get_conversation_with_messages(
        session, conversation_id
    )
    if not conversation_with_messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return SuccessResponse(data=conversation_with_messages)


@router.post("")
async def create_conversation(
    data: CreateConversationIn,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(authenticate),
    conversation_service: ConversationService = Depends(),
) -> SuccessResponse[ConversationOut]:
    conversation = await conversation_service.create_conversation(
        session, str(current_user.id), data
    )
    return SuccessResponse(data=conversation)


@router.patch("/conversation/{conversation_id}")
async def update_conversation(
    conversation_id: UUID,
    data: UpdateConversationRequest,
    session: AsyncSession = Depends(get_session),
    conversation_service: ConversationService = Depends(),
) -> SuccessResponse[ConversationOut]:
    conversation = await conversation_service.update_conversation(
        session, conversation_id, data
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return SuccessResponse(data=conversation)


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    session: AsyncSession = Depends(get_session),
    conversation_service: ConversationService = Depends(),
) -> SuccessResponse[None]:
    success = await conversation_service.delete_conversation(session, conversation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return SuccessResponse()
