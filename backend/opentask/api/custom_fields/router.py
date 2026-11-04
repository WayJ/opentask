"""Custom Fields API (E25)."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.custom_field.service import (
    CustomFieldService,
    require_writer,
    serialize_field,
)
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/custom-fields", tags=["Custom Fields"])


class CustomFieldCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    type: str = Field(..., description="text|number|single_select|multi_select|date|boolean")
    key: Optional[str] = Field(None, max_length=64)
    options: Optional[list[Any]] = None
    position: Optional[int] = None


class CustomFieldUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    options: Optional[list[Any]] = None
    setOptions: bool = False
    position: Optional[int] = None
    archive: Optional[bool] = None


class CustomFieldReorder(BaseModel):
    orderedIds: list[str] = Field(..., min_length=1)


@router.get("")
async def list_custom_fields(
    includeArchived: bool = Query(False),
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows = await CustomFieldService(session).list(
        workspace_id=ws.id, include_archived=includeArchived
    )
    payload = [serialize_field(r) for r in rows]
    return success_response(data={"rows": payload, "total": len(payload)})


@router.post("")
async def create_custom_field(
    body: CustomFieldCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    row = await CustomFieldService(session).create(
        workspace_id=ws.id,
        user_id=str(user.id),
        name=body.name,
        field_type=body.type,
        key=body.key,
        options=body.options,
        position=body.position,
    )
    return success_response(data=serialize_field(row), message="已创建")


@router.post("/reorder")
async def reorder_custom_fields(
    body: CustomFieldReorder,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    rows = await CustomFieldService(session).reorder(
        workspace_id=ws.id, ordered_ids=body.orderedIds
    )
    payload = [serialize_field(r) for r in rows]
    return success_response(data={"rows": payload, "total": len(payload)}, message="已排序")

@router.get("/{field_id}")
async def get_custom_field(
    field_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    row = await CustomFieldService(session).get(workspace_id=ws.id, field_id=field_id)
    return success_response(data=serialize_field(row))


@router.patch("/{field_id}")
async def update_custom_field(
    field_id: str,
    body: CustomFieldUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row = await CustomFieldService(session).update(
        workspace_id=ws.id,
        field_id=field_id,
        name=body.name,
        options=body.options,
        set_options=body.setOptions or body.options is not None,
        position=body.position,
        archive=body.archive,
    )
    return success_response(data=serialize_field(row), message="已更新")


@router.delete("/{field_id}")
async def delete_custom_field(
    field_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    await CustomFieldService(session).delete(workspace_id=ws.id, field_id=field_id)
    return success_response(data={"id": field_id}, message="已删除")


