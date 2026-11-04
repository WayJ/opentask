"""Entity Documents API (E10-S3) — Issue/Project/Initiative MD notes; no PGE."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.entity_document.model import ENTITY_DOC_PARENT_TYPES
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.entity_document.service import (
    EntityDocumentService,
    require_writer,
    serialize_entity_document,
)
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/entity-documents", tags=["Entity Documents"])


class DocCreate(BaseModel):
    parentType: str
    parentId: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=200)
    bodyMd: str = ""

    @field_validator("parentType")
    @classmethod
    def _pt(cls, v: str) -> str:
        if v not in ENTITY_DOC_PARENT_TYPES:
            raise ValueError(f"parentType must be one of {ENTITY_DOC_PARENT_TYPES}")
        return v


class DocUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    bodyMd: Optional[str] = None


@router.get("")
async def list_docs(
    parentType: str = Query(...),
    parentId: str = Query(...),
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    rows = await EntityDocumentService(session).list(
        workspace_id=ws.id, parent_type=parentType, parent_id=parentId
    )
    return success_response(
        data={"rows": [serialize_entity_document(r) for r in rows], "total": len(rows)}
    )


@router.post("")
async def create_doc(
    body: DocCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    row = await EntityDocumentService(session).create(
        workspace_id=ws.id,
        user_id=str(user.id),
        parent_type=body.parentType,
        parent_id=body.parentId,
        title=body.title,
        body_md=body.bodyMd,
    )
    return success_response(data=serialize_entity_document(row), message="已创建文档")


@router.get("/{doc_id}")
async def get_doc(
    doc_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    row = await EntityDocumentService(session).get(workspace_id=ws.id, doc_id=doc_id)
    return success_response(data=serialize_entity_document(row))


@router.patch("/{doc_id}")
async def update_doc(
    doc_id: str,
    body: DocUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row = await EntityDocumentService(session).update(
        workspace_id=ws.id,
        doc_id=doc_id,
        title=body.title,
        body_md=body.bodyMd,
    )
    return success_response(data=serialize_entity_document(row), message="已更新")


@router.delete("/{doc_id}")
async def delete_doc(
    doc_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    await EntityDocumentService(session).delete(workspace_id=ws.id, doc_id=doc_id)
    return success_response(data={"id": doc_id}, message="已删除")
