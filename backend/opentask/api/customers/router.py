"""Customers API (E22)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from opentask.api.workspace.deps import require_workspace_context
from opentask.models.user.model import UserModel
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.repositories.base import get_session
from opentask.services.customer.service import CustomerService, require_writer, serialize_customer
from opentask.utils.response import success_response

router = APIRouter(prefix="/api/customers", tags=["Customers"])


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    domains: Optional[list[str]] = None
    externalUrl: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    domains: Optional[list[str]] = None
    setDomains: bool = False
    externalUrl: Optional[str] = Field(None, max_length=500)
    clearExternalUrl: bool = False
    notes: Optional[str] = None
    clearNotes: bool = False


@router.get("")
async def list_customers(
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    svc = CustomerService(session)
    rows = await svc.list(workspace_id=ws.id)
    payload = [serialize_customer(r, request_count=c) for r, c in rows]
    return success_response(data={"rows": payload, "total": len(payload)})


@router.post("")
async def create_customer(
    body: CustomerCreate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, user = ctx
    require_writer(member)
    row = await CustomerService(session).create(
        workspace_id=ws.id,
        user_id=str(user.id),
        name=body.name,
        domains=body.domains,
        external_url=body.externalUrl,
        notes=body.notes,
    )
    return success_response(data=serialize_customer(row, request_count=0), message="已创建")


@router.get("/{customer_id}")
async def get_customer(
    customer_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, _member, _user = ctx
    svc = CustomerService(session)
    row = await svc.get(workspace_id=ws.id, customer_id=customer_id)
    listed = await svc.list(workspace_id=ws.id)
    count = next((c for r, c in listed if r.id == customer_id), 0)
    return success_response(data=serialize_customer(row, request_count=count))


@router.patch("/{customer_id}")
async def update_customer(
    customer_id: str,
    body: CustomerUpdate,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    row = await CustomerService(session).update(
        workspace_id=ws.id,
        customer_id=customer_id,
        name=body.name,
        domains=body.domains,
        set_domains=body.setDomains or body.domains is not None,
        external_url=body.externalUrl,
        clear_external_url=body.clearExternalUrl,
        notes=body.notes,
        clear_notes=body.clearNotes,
    )
    return success_response(data=serialize_customer(row), message="已更新")


@router.delete("/{customer_id}")
async def delete_customer(
    customer_id: str,
    ctx: tuple[Workspace, WorkspaceMember, UserModel] = Depends(require_workspace_context),
    session: AsyncSession = Depends(get_session),
):
    ws, member, _user = ctx
    require_writer(member)
    await CustomerService(session).delete(workspace_id=ws.id, customer_id=customer_id)
    return success_response(data={"id": customer_id}, message="已删除")
