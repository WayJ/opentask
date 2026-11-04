"""E17: workspace-scoped global search + tenant isolation."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "sr"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": password, "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "username": uname,
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
async def test_search_requires_workspace_header(test_client: AsyncClient):
    user = await _register(test_client, "sr_hdr")
    resp = await test_client.get(
        "/api/search",
        headers=_auth(user["token"]),
        params={"q": "x"},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_search_empty_query_returns_empty_groups(test_client: AsyncClient):
    user = await _register(test_client, "sr_empty")
    resp = await test_client.get(
        "/api/search",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"q": "   "},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["issues"] == []
    assert data["projects"] == []
    assert data["docs"] == []
    assert data["members"] == []


@pytest.mark.asyncio
async def test_search_hits_issue_project_doc_member_same_ws(test_client: AsyncClient):
    user = await _register(test_client, "sr_hit")
    h = _auth(user["token"], user["workspaceId"])
    marker = f"E17needle{uuid.uuid4().hex[:6]}"

    proj = await test_client.post(
        "/api/projects",
        headers=h,
        json={"name": f"Searchable Alpha {marker}", "description": "d"},
    )
    assert proj.status_code == 200, proj.text
    project_id = proj.json()["data"]["id"]

    issue = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": f"Fix {marker} login",
            "description": "x",
            "type": "bug",
            "status": "open",
            "priority": "medium",
            "reporter_id": user["userId"],
            "project_id": project_id,
        },
    )
    assert issue.status_code == 200, issue.text
    issue_body = issue.json()["data"]
    issue_code = issue_body["issue_code"]

    doc = await test_client.post(
        "/api/entity-documents",
        headers=h,
        json={
            "parentType": "project",
            "parentId": project_id,
            "title": f"Doc {marker}",
            "bodyMd": "searchable body",
        },
    )
    assert doc.status_code == 200, doc.text
    doc_id = doc.json()["data"]["id"]

    mem = await test_client.get(
        "/api/search",
        headers=h,
        params={"q": user["username"][:8]},
    )
    assert mem.status_code == 200, mem.text
    members = mem.json()["data"]["members"]
    assert any(m["userId"] == user["userId"] for m in members)

    by_title = await test_client.get(
        "/api/search",
        headers=h,
        params={"q": marker},
    )
    assert by_title.status_code == 200, by_title.text
    payload = by_title.json()["data"]
    assert any(i["id"] == issue_body["id"] for i in payload["issues"])
    assert any(p["id"] == project_id for p in payload["projects"])
    assert any(d["id"] == doc_id for d in payload["docs"])

    by_code = await test_client.get(
        "/api/search",
        headers=h,
        params={"q": issue_code},
    )
    assert by_code.status_code == 200, by_code.text
    assert any(i["issueCode"] == issue_code for i in by_code.json()["data"]["issues"])


@pytest.mark.asyncio
async def test_search_cross_tenant_forbidden(test_client: AsyncClient):
    a = await _register(test_client, "sr_a")
    b = await _register(test_client, "sr_b")
    resp = await test_client.get(
        "/api/search",
        headers=_auth(b["token"], a["workspaceId"]),
        params={"q": "anything"},
    )
    assert resp.status_code == 403, resp.text
