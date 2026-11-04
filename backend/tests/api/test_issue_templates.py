"""E9-S2：Workspace Issue Templates CRUD + seed + template_id create"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "tpl"):
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


async def _add_member(client: AsyncClient, owner: dict, member: dict, role: str = "member"):
    resp = await client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": role},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_list_auto_seeds_five_builtins(test_client: AsyncClient):
    user = await _register(test_client, "tpl_seed")
    listed = await test_client.get(
        "/api/issue-templates",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    data = listed.json()["data"]
    assert data["total"] == 5
    keys = {r["seedKey"] for r in data["rows"]}
    assert keys == {
        "bug_report",
        "feature_request",
        "improvement",
        "question",
        "task",
    }
    # idempotent
    listed2 = await test_client.get(
        "/api/issue-templates",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed2.json()["data"]["total"] == 5


@pytest.mark.asyncio
async def test_crud_custom_template(test_client: AsyncClient):
    user = await _register(test_client, "tpl_crud")
    # ensure seeds first
    await test_client.get(
        "/api/issue-templates",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    created = await test_client.post(
        "/api/issue-templates",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "name": "自定义发布清单",
            "description": "发版用",
            "icon": "i-carbon-list",
            "payload": {
                "type": "feature",
                "priority": "high",
                "title": "Release: ",
                "description": "## Checklist\n- [ ]",
            },
            "sortOrder": 10,
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["name"] == "自定义发布清单"
    assert row["source"] == "custom"
    assert row["payload"]["priority"] == "high"
    tid = row["id"]

    patched = await test_client.patch(
        f"/api/issue-templates/{tid}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "发布清单 v2", "payload": {"type": "feature", "priority": "medium"}},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["name"] == "发布清单 v2"
    assert patched.json()["data"]["payload"]["priority"] == "medium"

    deleted = await test_client.delete(
        f"/api/issue-templates/{tid}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert deleted.status_code == 200, deleted.text

    listed = await test_client.get(
        "/api/issue-templates",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    names = {r["name"] for r in listed.json()["data"]["rows"]}
    assert "发布清单 v2" not in names


@pytest.mark.asyncio
async def test_viewer_read_ok_write_forbidden(test_client: AsyncClient):
    owner = await _register(test_client, "tpl_own")
    viewer = await _register(test_client, "tpl_view")
    await _add_member(test_client, owner, viewer, role="viewer")
    listed = await test_client.get(
        "/api/issue-templates",
        headers=_auth(viewer["token"], owner["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["data"]["total"] == 5

    forbidden = await test_client.post(
        "/api/issue-templates",
        headers=_auth(viewer["token"], owner["workspaceId"]),
        json={"name": "nope"},
    )
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_cross_workspace_404(test_client: AsyncClient):
    a = await _register(test_client, "tpl_xa")
    b = await _register(test_client, "tpl_xb")
    await test_client.get(
        "/api/issue-templates",
        headers=_auth(a["token"], a["workspaceId"]),
    )
    rows = (
        await test_client.get(
            "/api/issue-templates",
            headers=_auth(a["token"], a["workspaceId"]),
        )
    ).json()["data"]["rows"]
    tid = rows[0]["id"]

    resp = await test_client.patch(
        f"/api/issue-templates/{tid}",
        headers=_auth(b["token"], b["workspaceId"]),
        json={"name": "hijack"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_name_rejected(test_client: AsyncClient):
    user = await _register(test_client, "tpl_dup")
    await test_client.get(
        "/api/issue-templates",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    # Bug 报告 is seeded
    resp = await test_client.post(
        "/api/issue-templates",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "Bug 报告", "payload": {"type": "bug"}},
    )
    assert resp.status_code in (400, 409)


@pytest.mark.asyncio
async def test_create_issue_with_template_id_merges_payload(test_client: AsyncClient):
    user = await _register(test_client, "tpl_ci")
    listed = await test_client.get(
        "/api/issue-templates",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    bug = next(r for r in listed.json()["data"]["rows"] if r["seedKey"] == "bug_report")

    created = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": "Login crash",
            "template_id": bug["id"],
            "reporter_id": user["userId"],
        },
    )
    assert created.status_code == 200, created.text
    data = created.json()["data"]
    assert data["title"] == "Login crash"
    assert data["type"] == "bug"
    # description from template payload should be present (non-empty seed body)
    assert data.get("description")


@pytest.mark.asyncio
async def test_create_issue_without_template_still_works(test_client: AsyncClient):
    user = await _register(test_client, "tpl_plain")
    created = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": "Plain issue",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "reporter_id": user["userId"],
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["data"]["title"] == "Plain issue"


@pytest.mark.asyncio
async def test_requires_workspace_header(test_client: AsyncClient):
    user = await _register(test_client, "tpl_hdr")
    resp = await test_client.get(
        "/api/issue-templates",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 400
