"""E68: public form → triage enqueue mid."""
from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

os.environ["OPENTASK_FORM_RATE_LIMIT"] = "0"

DEFAULT_FIELDS = [
    {"key": "title", "type": "title", "label": "标题", "required": True},
    {"key": "description", "type": "description", "label": "描述"},
]


async def _register(client: AsyncClient, prefix: str = "e68"):
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
        "username": uname,
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


@pytest.mark.asyncio
async def test_e68_form_enqueue_triage_default_false_and_patch(test_client: AsyncClient):
    user = await _register(test_client, "e68_crud")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post(
        "/api/forms",
        headers=h,
        json={"name": "TriageForm", "fields": DEFAULT_FIELDS},
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row.get("enqueueTriage") is False
    fid = row["id"]

    patched = await test_client.patch(
        f"/api/forms/{fid}",
        headers=h,
        json={"enqueueTriage": True},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["enqueueTriage"] is True

    got = await test_client.get(f"/api/forms/{fid}", headers=h)
    assert got.status_code == 200, got.text
    assert got.json()["data"]["enqueueTriage"] is True

    created_on = await test_client.post(
        "/api/forms",
        headers=h,
        json={
            "name": "TriageOn",
            "fields": DEFAULT_FIELDS,
            "enqueueTriage": True,
        },
    )
    assert created_on.status_code == 200, created_on.text
    assert created_on.json()["data"]["enqueueTriage"] is True
