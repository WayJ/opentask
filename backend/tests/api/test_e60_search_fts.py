"""E60: Search FTS mid — description hits, rank/snippet, isolation, no-emit."""
from __future__ import annotations

import uuid
from unittest import mock

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e60"):
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
async def test_e60_search_hits_issue_description(test_client: AsyncClient):
    user = await _register(test_client, "e60_desc")
    h = _auth(user["token"], user["workspaceId"])
    needle = f"uniqueDesc{uuid.uuid4().hex[:8]}"

    proj = await test_client.post(
        "/api/projects",
        headers=h,
        json={"name": f"P {needle[:6]}", "description": "d"},
    )
    assert proj.status_code == 200, proj.text
    project_id = proj.json()["data"]["id"]

    issue = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "Generic title without needle",
            "description": f"Body mentions {needle} clearly",
            "type": "bug",
            "status": "open",
            "priority": "medium",
            "reporter_id": user["userId"],
            "project_id": project_id,
        },
    )
    assert issue.status_code == 200, issue.text
    issue_id = issue.json()["data"]["id"]

    resp = await test_client.get(
        "/api/search",
        headers=h,
        params={"q": needle},
    )
    assert resp.status_code == 200, resp.text
    issues = resp.json()["data"]["issues"]
    assert any(i["id"] == issue_id for i in issues), issues
    hit = next(i for i in issues if i["id"] == issue_id)
    assert "rank" in hit
    assert hit.get("snippet") is None or len(hit["snippet"]) <= 120


@pytest.mark.asyncio
async def test_e60_search_project_description_and_doc_body(test_client: AsyncClient):
    user = await _register(test_client, "e60_pd")
    h = _auth(user["token"], user["workspaceId"])
    marker = f"pd{uuid.uuid4().hex[:8]}"

    proj = await test_client.post(
        "/api/projects",
        headers=h,
        json={"name": "Plain Name", "description": f"Project about {marker}"},
    )
    assert proj.status_code == 200, proj.text
    project_id = proj.json()["data"]["id"]

    doc = await test_client.post(
        "/api/entity-documents",
        headers=h,
        json={
            "parentType": "project",
            "parentId": project_id,
            "title": "Untitled note",
            "bodyMd": f"Long body with {marker} inside",
        },
    )
    assert doc.status_code == 200, doc.text
    doc_id = doc.json()["data"]["id"]

    resp = await test_client.get(
        "/api/search",
        headers=h,
        params={"q": marker},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert any(p["id"] == project_id for p in data["projects"]), data["projects"]
    assert any(d["id"] == doc_id for d in data["docs"]), data["docs"]
    doc_hit = next(d for d in data["docs"] if d["id"] == doc_id)
    assert len(doc_hit.get("snippet") or "") <= 120


@pytest.mark.asyncio
async def test_e60_search_exact_issue_code_still_first(test_client: AsyncClient):
    user = await _register(test_client, "e60_code")
    h = _auth(user["token"], user["workspaceId"])

    proj = await test_client.post(
        "/api/projects",
        headers=h,
        json={"name": "CodeProj", "description": "d"},
    )
    assert proj.status_code == 200, proj.text
    project_id = proj.json()["data"]["id"]

    issue = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "Code exact",
            "description": "x",
            "type": "bug",
            "status": "open",
            "priority": "medium",
            "reporter_id": user["userId"],
            "project_id": project_id,
        },
    )
    assert issue.status_code == 200, issue.text
    issue_code = issue.json()["data"]["issue_code"]

    resp = await test_client.get(
        "/api/search",
        headers=h,
        params={"q": issue_code},
    )
    assert resp.status_code == 200, resp.text
    issues = resp.json()["data"]["issues"]
    assert issues and issues[0]["issueCode"] == issue_code


@pytest.mark.asyncio
async def test_e60_search_cross_tenant_forbidden(test_client: AsyncClient):
    a = await _register(test_client, "e60_a")
    b = await _register(test_client, "e60_b")
    resp = await test_client.get(
        "/api/search",
        headers=_auth(b["token"], a["workspaceId"]),
        params={"q": "anything"},
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_e60_search_no_emit_fire_webhooks(test_client: AsyncClient):
    user = await _register(test_client, "e60_ne")
    h = _auth(user["token"], user["workspaceId"])
    with mock.patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new_callable=mock.AsyncMock,
    ) as fire_spy:
        resp = await test_client.get(
            "/api/search",
            headers=h,
            params={"q": "noop"},
        )
        assert resp.status_code == 200, resp.text
        fire_spy.assert_not_called()


@pytest.mark.asyncio
async def test_e60_search_empty_query_still_empty(test_client: AsyncClient):
    user = await _register(test_client, "e60_empty")
    resp = await test_client.get(
        "/api/search",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"q": "  "},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data == {"issues": [], "projects": [], "docs": [], "members": [], "comments": []}
