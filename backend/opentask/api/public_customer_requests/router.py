"""Public Customer Request status API — no auth (E63)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.repositories.base import get_session
from opentask.services.customer.service import (
    CustomerRequestService,
    check_public_rate_limit,
)
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/public/customer-requests", tags=["Public Customer Requests"])


class PublicReplyBody(BaseModel):
    body: str = Field(..., min_length=1, max_length=4000)


@router.get("/{token}")
async def public_request_status(
    token: str,
    session: AsyncSession = Depends(get_session),
):
    check_public_rate_limit(token)
    svc = CustomerRequestService(session)
    row = await svc.get_by_status_token(token)
    return success_response(data=await svc.serialize_public_card(row))


@router.post("/{token}/replies")
async def public_request_reply(
    token: str,
    body: PublicReplyBody,
    session: AsyncSession = Depends(get_session),
):
    check_public_rate_limit(token)
    svc = CustomerRequestService(session)
    result = await svc.add_public_reply(token=token, body=body.body)
    return success_response(data=result, message="已提交")
