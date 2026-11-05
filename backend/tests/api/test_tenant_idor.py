"""E15：租户 IDOR — 直读 UUID 必须验成员资格。"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "idor"):
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
        "password": password,
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


async def _create_project(client: AsyncClient, user: dict, name: str) -> dict:
    resp = await client.post(
        "/api/projects",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name, "description": "idor"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_issue(client: AsyncClient, user: dict, title: str) -> dict:
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": title, "type": "bug"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _denied(status: int) -> bool:
    return status in (403, 404)


@pytest.mark.asyncio
async def test_project_get_put_delete_cross_tenant_denied(test_client: AsyncClient):
    owner = await _register(test_client, "own")
    stranger = await _register(test_client, "str")
    project = await _create_project(test_client, owner, f"P-{uuid.uuid4().hex[:6]}")

    # stranger + 自己的 WS 头
    get_own_hdr = await test_client.get(
        f"/api/projects/{project['id']}",
        headers=_auth(stranger["token"], stranger["workspaceId"]),
    )
    assert _denied(get_own_hdr.status_code), get_own_hdr.text

    # stranger + 外域头（列表已 403；直读也不应放过实体）
    get_wrong = await test_client.get(
        f"/api/projects/{project['id']}",
        headers=_auth(stranger["token"], owner["workspaceId"]),
    )
    assert _denied(get_wrong.status_code), get_wrong.text

    # stranger 无头
    get_nohdr = await test_client.get(
        f"/api/projects/{project['id']}",
        headers=_auth(stranger["token"]),
    )
    assert _denied(get_nohdr.status_code), get_nohdr.text

    put = await test_client.put(
        f"/api/projects/{project['id']}",
        headers=_auth(stranger["token"], stranger["workspaceId"]),
        json={"description": "hijacked"},
    )
    assert _denied(put.status_code), put.text

    delete = await test_client.delete(
        f"/api/projects/{project['id']}",
        headers=_auth(stranger["token"], stranger["workspaceId"]),
    )
    assert _denied(delete.status_code), delete.text

    # 本租户仍可读改
    ok_get = await test_client.get(
        f"/api/projects/{project['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert ok_get.status_code == 200, ok_get.text
    assert ok_get.json()["data"]["name"] == project["name"]

    ok_put = await test_client.put(
        f"/api/projects/{project['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"description": "owner-ok"},
    )
    assert ok_put.status_code == 200, ok_put.text


@pytest.mark.asyncio
async def test_issue_uuid_cross_tenant_denied(test_client: AsyncClient):
    owner = await _register(test_client, "issown")
    stranger = await _register(test_client, "issstr")
    issue = await _create_issue(test_client, owner, "Secret issue")

    for headers in (
        _auth(stranger["token"], stranger["workspaceId"]),
        _auth(stranger["token"]),
    ):
        resp = await test_client.get(f"/api/issues/{issue['id']}", headers=headers)
        assert _denied(resp.status_code), resp.text

    # 外域头：deps 应 403
    foreign_hdr = await test_client.get(
        f"/api/issues/{issue['id']}",
        headers=_auth(stranger["token"], owner["workspaceId"]),
    )
    assert _denied(foreign_hdr.status_code), foreign_hdr.text

    put = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(stranger["token"], stranger["workspaceId"]),
        json={"title": "hijacked"},
    )
    assert _denied(put.status_code), put.text

    # 本租户仍通
    ok = await test_client.get(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["data"]["title"] == "Secret issue"


@pytest.mark.asyncio
async def test_issue_child_routes_cross_tenant_denied(test_client: AsyncClient):
    owner = await _register(test_client, "chown")
    stranger = await _register(test_client, "chstr")
    issue = await _create_issue(test_client, owner, "Child secret")
    iid = issue["id"]
    hdr = _auth(stranger["token"], stranger["workspaceId"])

    for path in (
        f"/api/issues/{iid}/comments",
        f"/api/issues/{iid}/relations",
        f"/api/issues/{iid}/attachments",
    ):
        resp = await test_client.get(path, headers=hdr)
        assert _denied(resp.status_code), (path, resp.text)

    post_c = await test_client.post(
        f"/api/issues/{iid}/comments",
        headers=hdr,
        json={"content": "nope"},
    )
    assert _denied(post_c.status_code), post_c.text


@pytest.mark.asyncio
async def test_list_wrong_workspace_header_still_403(test_client: AsyncClient):
    a = await _register(test_client, "lista")
    b = await _register(test_client, "listb")
    resp = await test_client.get(
        "/api/projects",
        headers=_auth(a["token"], b["workspaceId"]),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_issue_by_code_does_not_leak_across_workspace(test_client: AsyncClient):
    owner = await _register(test_client, "codeown")
    stranger = await _register(test_client, "codestr")
    issue = await _create_issue(test_client, owner, "Coded")
    code = issue.get("issue_code") or issue.get("issueCode")
    assert code, issue

    # stranger 用自己的 WS 头 + by_code → 不应拿到 owner 的单
    resp = await test_client.get(
        f"/api/issues/{code}",
        params={"by_code": "true"},
        headers=_auth(stranger["token"], stranger["workspaceId"]),
    )
    assert _denied(resp.status_code) or (
        resp.status_code == 200 and resp.json().get("data") is None
    ), resp.text
    if resp.status_code == 200:
        # 部分实现用业务码 404
        body = resp.json()
        assert body.get("code") in (404, None) or body.get("data") in (None, {}), body
