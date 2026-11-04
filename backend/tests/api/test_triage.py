"""E9-S1：Workspace Triage 队列（accept / decline / duplicate）"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "tri"):
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


async def _add_member(client: AsyncClient, owner: dict, member: dict, role: str = "member"):
    resp = await client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": role},
    )
    assert resp.status_code == 200, resp.text


async def _create_issue(client: AsyncClient, user: dict, title: str, **extra) -> dict:
    body = {
        "title": title,
        "type": "feature",
        "status": "open",
        "priority": "medium",
        "reporter_id": user["userId"],
        **extra,
    }
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_enqueue_list_and_idempotent(test_client: AsyncClient):
    user = await _register(test_client, "tri_e")
    issue = await _create_issue(test_client, user, "Needs triage")

    enq = await test_client.post(
        "/api/triage",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"issueId": issue["id"]},
    )
    assert enq.status_code == 200, enq.text
    row = enq.json()["data"]
    assert row["id"] == issue["id"]
    assert row["triageStatus"] == "pending"
    assert row["title"] == "Needs triage"
    assert row["issueCode"]
    assert row["workspaceId"] == user["workspaceId"]

    enq2 = await test_client.post(
        "/api/triage",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"issueId": issue["id"]},
    )
    assert enq2.status_code == 200, enq2.text
    assert enq2.json()["data"]["id"] == issue["id"]

    listed = await test_client.get(
        "/api/triage",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    data = listed.json()["data"]
    assert data["total"] == 1
    assert data["rows"][0]["id"] == issue["id"]
    assert data["rows"][0]["triageStatus"] == "pending"


@pytest.mark.asyncio
async def test_create_and_enqueue(test_client: AsyncClient):
    user = await _register(test_client, "tri_c")
    created = await test_client.post(
        "/api/triage",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": "Inbound bug",
            "type": "bug",
            "priority": "high",
            "description": "from form",
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["title"] == "Inbound bug"
    assert row["type"] == "bug"
    assert row["priority"] == "high"
    assert row["triageStatus"] == "pending"
    assert row["status"] == "open"

    listed = await test_client.get(
        "/api/triage",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.json()["data"]["total"] == 1


@pytest.mark.asyncio
async def test_accept_clears_triage_and_opens(test_client: AsyncClient):
    user = await _register(test_client, "tri_a")
    issue = await _create_issue(test_client, user, "Accept me", status="rejected")
    await test_client.post(
        "/api/triage",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"issueId": issue["id"]},
    )

    acc = await test_client.post(
        f"/api/triage/{issue['id']}/accept",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert acc.status_code == 200, acc.text
    data = acc.json()["data"]
    assert data["status"] == "open"
    assert data.get("triageStatus") in (None, "")

    listed = await test_client.get(
        "/api/triage",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_decline_rejects_and_leaves_queue(test_client: AsyncClient):
    user = await _register(test_client, "tri_d")
    issue = await _create_issue(test_client, user, "Decline me")
    await test_client.post(
        "/api/triage",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"issueId": issue["id"]},
    )

    dec = await test_client.post(
        f"/api/triage/{issue['id']}/decline",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert dec.status_code == 200, dec.text
    assert dec.json()["data"]["status"] == "rejected"
    assert dec.json()["data"].get("triageStatus") in (None, "")

    listed = await test_client.get(
        "/api/triage",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_duplicate_creates_relation_and_declines(test_client: AsyncClient):
    user = await _register(test_client, "tri_dup")
    canonical = await _create_issue(test_client, user, "Canonical")
    dup = await _create_issue(test_client, user, "Dup inbound")
    await test_client.post(
        "/api/triage",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"issueId": dup["id"]},
    )

    resp = await test_client.post(
        f"/api/triage/{dup['id']}/duplicate",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"duplicateOfIssueId": canonical["id"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "rejected"

    listed = await test_client.get(
        "/api/triage",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.json()["data"]["total"] == 0

    rels = await test_client.get(
        f"/api/issues/{dup['id']}/relations",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert rels.status_code == 200, rels.text
    payload = rels.json()["data"]
    as_source = payload.get("as_source") or []
    # pydantic may dump as model or dict
    def _rt(r):
        if hasattr(r, "relation_type"):
            return getattr(r, "relation_type")
        return r.get("relation_type") or r.get("relationType")

    def _tid(r):
        if hasattr(r, "target_id"):
            return getattr(r, "target_id")
        return r.get("target_id") or r.get("targetId")

    assert any(_rt(r) == "duplicates" and _tid(r) == canonical["id"] for r in as_source), payload


@pytest.mark.asyncio
async def test_viewer_read_ok_write_forbidden(test_client: AsyncClient):
    owner = await _register(test_client, "tri_own")
    viewer = await _register(test_client, "tri_view")
    await _add_member(test_client, owner, viewer, role="viewer")
    issue = await _create_issue(test_client, owner, "Owner issue")
    await test_client.post(
        "/api/triage",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"issueId": issue["id"]},
    )

    listed = await test_client.get(
        "/api/triage",
        headers=_auth(viewer["token"], owner["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    assert listed.json()["data"]["total"] == 1

    forbidden = await test_client.post(
        f"/api/triage/{issue['id']}/accept",
        headers=_auth(viewer["token"], owner["workspaceId"]),
    )
    assert forbidden.status_code == 403

    enq = await test_client.post(
        "/api/triage",
        headers=_auth(viewer["token"], owner["workspaceId"]),
        json={"title": "viewer create"},
    )
    assert enq.status_code == 403


@pytest.mark.asyncio
async def test_cross_workspace_issue_404(test_client: AsyncClient):
    a = await _register(test_client, "tri_xa")
    b = await _register(test_client, "tri_xb")
    issue_b = await _create_issue(test_client, b, "B only")

    enq = await test_client.post(
        "/api/triage",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"issueId": issue_b["id"]},
    )
    assert enq.status_code == 404

    # put in B's triage then try accept from A
    await test_client.post(
        "/api/triage",
        headers=_auth(b["token"], b["workspaceId"]),
        json={"issueId": issue_b["id"]},
    )
    acc = await test_client.post(
        f"/api/triage/{issue_b['id']}/accept",
        headers=_auth(a["token"], a["workspaceId"]),
    )
    assert acc.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_target_other_ws_404(test_client: AsyncClient):
    a = await _register(test_client, "tri_da")
    b = await _register(test_client, "tri_db")
    issue_a = await _create_issue(test_client, a, "A pending")
    issue_b = await _create_issue(test_client, b, "B canonical")
    await test_client.post(
        "/api/triage",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"issueId": issue_a["id"]},
    )
    resp = await test_client.post(
        f"/api/triage/{issue_a['id']}/duplicate",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"duplicateOfIssueId": issue_b["id"]},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_accept_non_pending_400(test_client: AsyncClient):
    user = await _register(test_client, "tri_np")
    issue = await _create_issue(test_client, user, "Not pending")
    resp = await test_client.post(
        f"/api/triage/{issue['id']}/accept",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_triage_requires_workspace_header(test_client: AsyncClient):
    user = await _register(test_client, "tri_hdr")
    resp = await test_client.get(
        "/api/triage",
        headers=_auth(user["token"]),
    )
    assert resp.status_code == 400
