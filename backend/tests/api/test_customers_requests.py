"""E22：Customers + CustomerRequests + Issue M2M + 跨租户."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "cust"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str = "linked") -> dict:
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": title, "type": "feature", "status": "open", "priority": "medium"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_customer_crud(test_client: AsyncClient):
    user = await _register(test_client, "c_crud")
    h = _auth(user["token"], user["workspaceId"])

    created = await test_client.post(
        "/api/customers",
        headers=h,
        json={
            "name": "Acme Corp",
            "domains": ["acme.com", "acme.io"],
            "externalUrl": "https://acme.com",
            "notes": "优先客户",
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["name"] == "Acme Corp"
    assert row["domains"] == ["acme.com", "acme.io"]
    assert row["workspaceId"] == user["workspaceId"]
    assert row["requestCount"] == 0
    cid = row["id"]

    listed = await test_client.get("/api/customers", headers=h)
    assert listed.status_code == 200, listed.text
    data = listed.json()["data"]
    assert data["total"] >= 1
    assert any(r["id"] == cid for r in data["rows"])

    got = await test_client.get(f"/api/customers/{cid}", headers=h)
    assert got.status_code == 200, got.text
    assert got.json()["data"]["name"] == "Acme Corp"

    patched = await test_client.patch(
        f"/api/customers/{cid}",
        headers=h,
        json={"name": "Acme Inc", "domains": ["acme.com"], "setDomains": True},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["name"] == "Acme Inc"
    assert patched.json()["data"]["domains"] == ["acme.com"]

    deleted = await test_client.delete(f"/api/customers/{cid}", headers=h)
    assert deleted.status_code == 200, deleted.text
    missing = await test_client.get(f"/api/customers/{cid}", headers=h)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_customer_duplicate_name(test_client: AsyncClient):
    user = await _register(test_client, "c_dup")
    h = _auth(user["token"], user["workspaceId"])
    r1 = await test_client.post("/api/customers", headers=h, json={"name": "同名客户"})
    assert r1.status_code == 200, r1.text
    r2 = await test_client.post("/api/customers", headers=h, json={"name": "同名客户"})
    assert r2.status_code in (400, 409), r2.text


@pytest.mark.asyncio
async def test_customer_viewer_read_ok_write_forbidden(test_client: AsyncClient):
    owner = await _register(test_client, "c_own")
    viewer = await _register(test_client, "c_view")
    await _add_member(test_client, owner, viewer, role="viewer")
    oh = _auth(owner["token"], owner["workspaceId"])
    vh = _auth(viewer["token"], owner["workspaceId"])

    created = await test_client.post("/api/customers", headers=oh, json={"name": "可见客户"})
    assert created.status_code == 200, created.text
    cid = created.json()["data"]["id"]

    listed = await test_client.get("/api/customers", headers=vh)
    assert listed.status_code == 200, listed.text

    forbidden = await test_client.post("/api/customers", headers=vh, json={"name": "不可写"})
    assert forbidden.status_code == 403, forbidden.text

    patch_forbidden = await test_client.patch(
        f"/api/customers/{cid}", headers=vh, json={"notes": "nope"}
    )
    assert patch_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_customer_cross_workspace_404(test_client: AsyncClient):
    a = await _register(test_client, "c_a")
    b = await _register(test_client, "c_b")
    created = await test_client.post(
        "/api/customers",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"name": "仅 A"},
    )
    assert created.status_code == 200, created.text
    cid = created.json()["data"]["id"]

    other = await test_client.get(
        f"/api/customers/{cid}",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert other.status_code == 404


@pytest.mark.asyncio
async def test_request_crud_filter_and_link(test_client: AsyncClient):
    user = await _register(test_client, "r_crud")
    h = _auth(user["token"], user["workspaceId"])

    cust = await test_client.post("/api/customers", headers=h, json={"name": "Beta"})
    assert cust.status_code == 200, cust.text
    customer_id = cust.json()["data"]["id"]

    issue = await _create_issue(test_client, user, "feat-from-req")

    created = await test_client.post(
        "/api/customer-requests",
        headers=h,
        json={
            "customerId": customer_id,
            "title": "需要 SSO",
            "body": "企业登录",
            "priority": "high",
            "issueIds": [issue["id"]],
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["title"] == "需要 SSO"
    assert row["status"] == "open"
    assert row["priority"] == "high"
    assert issue["id"] in row["issueIds"]
    rid = row["id"]

    listed = await test_client.get(
        "/api/customer-requests",
        headers=h,
        params={"customerId": customer_id, "status": "open"},
    )
    assert listed.status_code == 200, listed.text
    assert any(r["id"] == rid for r in listed.json()["data"]["rows"])

    by_issue = await test_client.get(
        "/api/customer-requests",
        headers=h,
        params={"issueId": issue["id"]},
    )
    assert by_issue.status_code == 200, by_issue.text
    assert by_issue.json()["data"]["total"] >= 1

    patched = await test_client.patch(
        f"/api/customer-requests/{rid}",
        headers=h,
        json={"status": "completed"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["status"] == "completed"

    issue2 = await _create_issue(test_client, user, "another")
    linked = await test_client.post(
        f"/api/customer-requests/{rid}/issues",
        headers=h,
        json={"issueId": issue2["id"]},
    )
    assert linked.status_code == 200, linked.text
    assert issue2["id"] in linked.json()["data"]["issueIds"]

    unlinked = await test_client.delete(
        f"/api/customer-requests/{rid}/issues/{issue['id']}",
        headers=h,
    )
    assert unlinked.status_code == 200, unlinked.text
    assert issue["id"] not in unlinked.json()["data"]["issueIds"]

    deleted = await test_client.delete(f"/api/customer-requests/{rid}", headers=h)
    assert deleted.status_code == 200, deleted.text


@pytest.mark.asyncio
async def test_create_and_link_issue(test_client: AsyncClient):
    user = await _register(test_client, "r_link")
    h = _auth(user["token"], user["workspaceId"])
    cust = await test_client.post("/api/customers", headers=h, json={"name": "Gamma"})
    customer_id = cust.json()["data"]["id"]

    created = await test_client.post(
        "/api/customer-requests",
        headers=h,
        json={
            "customerId": customer_id,
            "title": "导出报表",
            "body": "CSV 即可",
            "createAndLinkIssue": True,
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["issueCount"] == 1
    assert len(row["issueIds"]) == 1
    issues = row.get("issues") or []
    assert issues and issues[0]["title"] == "导出报表"


@pytest.mark.asyncio
async def test_request_viewer_and_cross_tenant(test_client: AsyncClient):
    owner = await _register(test_client, "r_own")
    viewer = await _register(test_client, "r_view")
    other = await _register(test_client, "r_other")
    await _add_member(test_client, owner, viewer, role="viewer")
    oh = _auth(owner["token"], owner["workspaceId"])
    vh = _auth(viewer["token"], owner["workspaceId"])

    cust = await test_client.post("/api/customers", headers=oh, json={"name": "Delta"})
    customer_id = cust.json()["data"]["id"]
    created = await test_client.post(
        "/api/customer-requests",
        headers=oh,
        json={"customerId": customer_id, "title": "只读可见"},
    )
    assert created.status_code == 200, created.text
    rid = created.json()["data"]["id"]

    listed = await test_client.get("/api/customer-requests", headers=vh)
    assert listed.status_code == 200, listed.text

    forbidden = await test_client.post(
        "/api/customer-requests",
        headers=vh,
        json={"customerId": customer_id, "title": "不可写"},
    )
    assert forbidden.status_code == 403

    cross = await test_client.get(
        f"/api/customer-requests/{rid}",
        headers=_auth(other["token"], other["workspaceId"]),
    )
    assert cross.status_code == 404
