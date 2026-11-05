"""E16: orphan Default Workspace must never leak into list; cleanup deletes it."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.services.workspace.service import (
    DEFAULT_WORKSPACE_ID,
    WorkspaceService,
)


async def _register(client: AsyncClient, prefix: str = "ow"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": password, "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


async def _ensure_orphan(session, *, with_member: bool = False) -> Workspace:
    ws = await session.get(Workspace, DEFAULT_WORKSPACE_ID)
    if ws is None:
        ws = Workspace(
            id=DEFAULT_WORKSPACE_ID,
            name="Default Workspace",
            slug=f"default-{uuid.uuid4().hex[:6]}",
            description="orphan seed",
            created_by=None,
            issue_key=f"D{uuid.uuid4().hex[:5]}".upper()[:6],
        )
        session.add(ws)
        await session.flush()
    if with_member:
        existing = (
            await session.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == DEFAULT_WORKSPACE_ID
                )
            )
        ).scalars().first()
        if existing is None:
            session.add(
                WorkspaceMember(
                    workspace_id=DEFAULT_WORKSPACE_ID,
                    user_id=f"keep-{uuid.uuid4().hex[:8]}",
                    role="owner",
                )
            )
    else:
        members = (
            await session.execute(
                select(WorkspaceMember).where(
                    WorkspaceMember.workspace_id == DEFAULT_WORKSPACE_ID
                )
            )
        ).scalars().all()
        for m in members:
            await session.delete(m)
    await session.commit()
    return ws


@pytest.mark.asyncio
async def test_list_never_includes_default_workspace_id(
    test_client: AsyncClient, test_session
):
    user = await _register(test_client, "ow_list")
    await _ensure_orphan(test_session, with_member=False)

    resp = await test_client.get(
        "/api/workspaces",
        headers={"Authorization": f"Bearer {user['token']}"},
    )
    assert resp.status_code == 200, resp.text
    ids = [row["id"] for row in resp.json()["data"]]
    assert DEFAULT_WORKSPACE_ID not in ids
    assert user["workspaceId"] in ids


@pytest.mark.asyncio
async def test_cleanup_deletes_memberless_default_workspace(test_session):
    await _ensure_orphan(test_session, with_member=False)

    svc = WorkspaceService(test_session)
    result = await svc.cleanup_orphan_default_workspace()
    await test_session.commit()
    assert result["deleted"] is True
    assert await test_session.get(Workspace, DEFAULT_WORKSPACE_ID) is None

    result2 = await svc.cleanup_orphan_default_workspace()
    assert result2["deleted"] is False
    assert result2["reason"] == "missing"


@pytest.mark.asyncio
async def test_cleanup_preserves_default_workspace_with_members(test_session):
    await _ensure_orphan(test_session, with_member=True)

    svc = WorkspaceService(test_session)
    result = await svc.cleanup_orphan_default_workspace()
    assert result["deleted"] is False
    assert result["reason"] == "has_members"
    assert await test_session.get(Workspace, DEFAULT_WORKSPACE_ID) is not None

    # Teardown so later tests see a clean slate
    members = (
        await test_session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == DEFAULT_WORKSPACE_ID
            )
        )
    ).scalars().all()
    for m in members:
        await test_session.delete(m)
    await test_session.commit()
    await svc.cleanup_orphan_default_workspace()
    await test_session.commit()
