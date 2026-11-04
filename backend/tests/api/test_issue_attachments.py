"""E11-S4: Issue attachments empty list must be 200 + []."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "att"):
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


def _auth(token: str, workspace_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


@pytest.mark.asyncio
async def test_empty_attachments_returns_200_and_list(test_client: AsyncClient):
    user = await _register(test_client, "att_empty")
    created = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": "NoAtt", "type": "bug", "reporter_id": user["userId"]},
    )
    assert created.status_code == 200, created.text
    issue_id = created.json()["data"]["id"]
    resp = await test_client.get(
        f"/api/issues/{issue_id}/attachments",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 200
    assert body["data"] == []


@pytest.mark.asyncio
async def test_documents_table_exists(test_engine):
    """Regression: live smoke failed because documents was never migrated."""
    from sqlalchemy import text

    async with test_engine.connect() as conn:
        row = await conn.execute(
            text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name='documents'"
            )
        )
        assert row.first() is not None
