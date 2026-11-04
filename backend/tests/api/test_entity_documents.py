"""E10-S3：entity_documents light MD on issue|project|initiative (no PGE)"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "ed"):
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


async def _create_project(client: AsyncClient, user: dict, name: str | None = None) -> dict:
    resp = await client.post(
        "/api/projects",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name or f"Proj-{uuid.uuid4().hex[:6]}"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_issue(client: AsyncClient, user: dict, title: str = "Doc Issue") -> dict:
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": title,
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "reporter_id": user["userId"],
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_initiative(client: AsyncClient, user: dict, name: str = "Doc Ini") -> dict:
    resp = await client.post(
        "/api/initiatives",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_crud_on_initiative(test_client: AsyncClient):
    user = await _register(test_client, "ed_ini")
    h = _auth(user["token"], user["workspaceId"])
    ini = await _create_initiative(test_client, user)

    created = await test_client.post(
        "/api/entity-documents",
        headers=h,
        json={
            "parentType": "initiative",
            "parentId": ini["id"],
            "title": "目标说明",
            "bodyMd": "## Why\n跨项目目标",
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["parentType"] == "initiative"
    assert row["parentId"] == ini["id"]
    assert row["title"] == "目标说明"
    assert "跨项目" in row["bodyMd"]
    did = row["id"]

    listed = await test_client.get(
        "/api/entity-documents",
        headers=h,
        params={"parentType": "initiative", "parentId": ini["id"]},
    )
    assert listed.status_code == 200, listed.text
    data = listed.json()["data"]
    assert data["total"] >= 1
    assert any(r["id"] == did for r in data["rows"])

    patched = await test_client.patch(
        f"/api/entity-documents/{did}",
        headers=h,
        json={"title": "目标说明 v2", "bodyMd": "updated"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["title"] == "目标说明 v2"

    deleted = await test_client.delete(f"/api/entity-documents/{did}", headers=h)
    assert deleted.status_code == 200, deleted.text
    missing = await test_client.get(f"/api/entity-documents/{did}", headers=h)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_crud_on_issue_and_project(test_client: AsyncClient):
    user = await _register(test_client, "ed_ip")
    h = _auth(user["token"], user["workspaceId"])
    issue = await _create_issue(test_client, user)
    project = await _create_project(test_client, user)

    for parent_type, parent_id in (("issue", issue["id"]), ("project", project["id"])):
        resp = await test_client.post(
            "/api/entity-documents",
            headers=h,
            json={
                "parentType": parent_type,
                "parentId": parent_id,
                "title": f"note-{parent_type}",
                "bodyMd": "md",
            },
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["parentType"] == parent_type


@pytest.mark.asyncio
async def test_invalid_parent_type_and_missing_parent(test_client: AsyncClient):
    user = await _register(test_client, "ed_bad")
    h = _auth(user["token"], user["workspaceId"])

    bad_type = await test_client.post(
        "/api/entity-documents",
        headers=h,
        json={
            "parentType": "requirement",
            "parentId": str(uuid.uuid4()),
            "title": "PGE forbidden",
        },
    )
    assert bad_type.status_code in (400, 422), bad_type.text

    missing = await test_client.post(
        "/api/entity-documents",
        headers=h,
        json={
            "parentType": "initiative",
            "parentId": str(uuid.uuid4()),
            "title": "ghost",
        },
    )
    assert missing.status_code == 404, missing.text


@pytest.mark.asyncio
async def test_viewer_read_ok_write_forbidden(test_client: AsyncClient):
    owner = await _register(test_client, "ed_own")
    viewer = await _register(test_client, "ed_view")
    await _add_member(test_client, owner, viewer, role="viewer")
    oh = _auth(owner["token"], owner["workspaceId"])
    vh = _auth(viewer["token"], owner["workspaceId"])
    ini = await _create_initiative(test_client, owner, "可见文档父")

    created = await test_client.post(
        "/api/entity-documents",
        headers=oh,
        json={"parentType": "initiative", "parentId": ini["id"], "title": "只读可见"},
    )
    assert created.status_code == 200, created.text

    listed = await test_client.get(
        "/api/entity-documents",
        headers=vh,
        params={"parentType": "initiative", "parentId": ini["id"]},
    )
    assert listed.status_code == 200

    forbidden = await test_client.post(
        "/api/entity-documents",
        headers=vh,
        json={"parentType": "initiative", "parentId": ini["id"], "title": "不可写"},
    )
    assert forbidden.status_code == 403


@pytest.mark.asyncio
async def test_cross_workspace_404(test_client: AsyncClient):
    a = await _register(test_client, "ed_a")
    b = await _register(test_client, "ed_b")
    ini = await _create_initiative(test_client, a)
    created = await test_client.post(
        "/api/entity-documents",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"parentType": "initiative", "parentId": ini["id"], "title": "仅A"},
    )
    assert created.status_code == 200
    did = created.json()["data"]["id"]

    other = await test_client.get(
        f"/api/entity-documents/{did}",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert other.status_code == 404

    # cannot attach B's doc to A's initiative from B listing either
    listed = await test_client.get(
        "/api/entity-documents",
        headers=_auth(b["token"], b["workspaceId"]),
        params={"parentType": "initiative", "parentId": ini["id"]},
    )
    assert listed.status_code in (200, 404)
    if listed.status_code == 200:
        assert listed.json()["data"]["total"] == 0
