"""Public Issue Forms API — no auth (E31)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.repositories.base import get_session
from opentask.services.issue_form.service import (
    IssueFormService,
    serialize_public_schema,
)
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/public/forms", tags=["Public Forms"])


class FormSubmitBody(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


@router.get("/{token}")
async def public_form_schema(
    token: str,
    session: AsyncSession = Depends(get_session),
):
    row = await IssueFormService(session).get_by_token(token, require_enabled=True)
    return success_response(data=serialize_public_schema(row))


@router.post("/{token}/submit")
async def public_form_submit(
    token: str,
    body: FormSubmitBody,
    session: AsyncSession = Depends(get_session),
):
    result = await IssueFormService(session).submit(token=token, values=body.values or {})
    return success_response(data=result, message="已提交")
