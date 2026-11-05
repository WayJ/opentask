"""Issue Forms admin API (E31)."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.issue_form.service import (
    IssueFormService,
    require_owner,
    require_reader,
    serialize_form,
)
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/forms", tags=["Forms"])


class FormCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    fields: list[Any] = Field(..., min_length=1)
    description: Optional[str] = None
    slug: Optional[str] = Field(None, max_length=80)
    enabled: bool = True
    createCustomerRequest: bool = False
    enqueueTriage: bool = False


class FormUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    fields: Optional[list[Any]] = None
    description: Optional[str] = None
    clearDescription: bool = False
    slug: Optional[str] = Field(None, max_length=80)
    setSlug: bool = False
    enabled: Optional[bool] = None
    createCustomerRequest: Optional[bool] = None
    enqueueTriage: Optional[bool] = None


@router.get("")
async def list_forms(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_reader(member)
    rows = await IssueFormService(session).list(workspace_id=ws.id)
    payload = [serialize_form(r) for r in rows]
    return success_response(data={"rows": payload, "total": len(payload)})


@router.post("")
async def create_form(
    body: FormCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_owner(member)
    row = await IssueFormService(session).create(
        workspace_id=ws.id,
        user_id=str(user.id),
        name=body.name,
        fields=body.fields,
        description=body.description,
        slug=body.slug,
        enabled=body.enabled,
        create_customer_request=body.createCustomerRequest,
        enqueue_triage=body.enqueueTriage,
    )
    return success_response(data=serialize_form(row), message="已创建")


@router.get("/{form_id}")
async def get_form(
    form_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_reader(member)
    row = await IssueFormService(session).get(workspace_id=ws.id, form_id=form_id)
    return success_response(data=serialize_form(row))


@router.patch("/{form_id}")
async def update_form(
    form_id: str,
    body: FormUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_owner(member)
    row = await IssueFormService(session).update(
        workspace_id=ws.id,
        form_id=form_id,
        name=body.name,
        description=body.description,
        clear_description=body.clearDescription,
        slug=body.slug,
        set_slug=body.setSlug or body.slug is not None,
        enabled=body.enabled,
        fields=body.fields,
        create_customer_request=body.createCustomerRequest,
        enqueue_triage=body.enqueueTriage,
    )
    return success_response(data=serialize_form(row), message="已更新")


@router.delete("/{form_id}")
async def delete_form(
    form_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_owner(member)
    await IssueFormService(session).delete(workspace_id=ws.id, form_id=form_id)
    return success_response(data={"id": form_id}, message="已删除")


@router.post("/{form_id}/regenerate-token")
async def regenerate_token(
    form_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_owner(member)
    row = await IssueFormService(session).regenerate_token(
        workspace_id=ws.id, form_id=form_id
    )
    return success_response(data=serialize_form(row), message="已重新生成 token")
