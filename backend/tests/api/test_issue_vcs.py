"""E11-S1: branch-name + issue_vcs_links API (Issue axis; not PGE)."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "vcs"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str = "Fix Login Redirect") -> dict:
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


@pytest.mark.asyncio
async def test_branch_name_suggest(test_client: AsyncClient):
    user = await _register(test_client, "bn")
    h = _auth(user["token"], user["workspaceId"])
    issue = await _create_issue(test_client, user, title="Fix Login Redirect")
    code = issue["issue_code"]

    resp = await test_client.get(f"/api/issues/{issue['id']}/vcs/branch-name", headers=h)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["issueCode"] == code
    assert data["slug"] == "fix-login-redirect"
    assert data["branchName"] == f"{code}-fix-login-redirect"


@pytest.mark.asyncio
async def test_branch_name_empty_title(test_client: AsyncClient):
    user = await _register(test_client, "bne")
    h = _auth(user["token"], user["workspaceId"])
    issue = await _create_issue(test_client, user, title="x")
    # Patch title to empty if API allows; else create with minimal
    # Use suggest on short title
    resp = await test_client.get(f"/api/issues/{issue['id']}/vcs/branch-name", headers=h)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["branchName"].startswith(issue["issue_code"])


@pytest.mark.asyncio
async def test_vcs_link_branch_crud(test_client: AsyncClient):
    user = await _register(test_client, "vl")
    h = _auth(user["token"], user["workspaceId"])
    issue = await _create_issue(test_client, user)
    bn = await test_client.get(f"/api/issues/{issue['id']}/vcs/branch-name", headers=h)
    branch_name = bn.json()["data"]["branchName"]

    created = await test_client.post(
        f"/api/issues/{issue['id']}/vcs/links",
        headers=h,
        json={"kind": "branch", "branchName": branch_name, "provider": "manual"},
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["kind"] == "branch"
    assert row["branchName"] == branch_name
    assert row["issueId"] == issue["id"]
    assert row["status"] == "unknown"
    link_id = row["id"]

    listed = await test_client.get(f"/api/issues/{issue['id']}/vcs/links", headers=h)
    assert listed.status_code == 200, listed.text
    data = listed.json()["data"]
    assert data["total"] >= 1
    assert any(r["id"] == link_id for r in data["rows"])

    # PR kind skeleton allowed in S1
    pr = await test_client.post(
        f"/api/issues/{issue['id']}/vcs/links",
        headers=h,
        json={
            "kind": "pull_request",
            "prUrl": "https://github.com/org/repo/pull/1",
            "branchName": branch_name,
            "provider": "github",
            "status": "open",
            "externalId": "1",
            "title": "Fix login",
        },
    )
    assert pr.status_code == 200, pr.text
    assert pr.json()["data"]["kind"] == "pull_request"
    assert pr.json()["data"]["prUrl"].endswith("/pull/1")

    deleted = await test_client.delete(
        f"/api/issues/{issue['id']}/vcs/links/{link_id}", headers=h
    )
    assert deleted.status_code == 200, deleted.text
    listed2 = await test_client.get(f"/api/issues/{issue['id']}/vcs/links", headers=h)
    ids = [r["id"] for r in listed2.json()["data"]["rows"]]
    assert link_id not in ids


@pytest.mark.asyncio
async def test_vcs_invalid_kind_and_viewer_forbidden(test_client: AsyncClient):
    owner = await _register(test_client, "vo")
    viewer = await _register(test_client, "vv")
    await _add_member(test_client, owner, viewer, role="viewer")
    issue = await _create_issue(test_client, owner)
    oh = _auth(owner["token"], owner["workspaceId"])
    vh = _auth(viewer["token"], owner["workspaceId"])

    bad = await test_client.post(
        f"/api/issues/{issue['id']}/vcs/links",
        headers=oh,
        json={"kind": "requirement", "branchName": "x"},
    )
    assert bad.status_code == 422 or bad.status_code == 400

    # viewer can read branch-name
    bn = await test_client.get(f"/api/issues/{issue['id']}/vcs/branch-name", headers=vh)
    assert bn.status_code == 200, bn.text

    # viewer cannot write
    w = await test_client.post(
        f"/api/issues/{issue['id']}/vcs/links",
        headers=vh,
        json={"kind": "branch", "branchName": "WAY-1-x"},
    )
    assert w.status_code == 403, w.text


@pytest.mark.asyncio
async def test_vcs_cross_workspace_404(test_client: AsyncClient):
    a = await _register(test_client, "wa")
    b = await _register(test_client, "wb")
    issue = await _create_issue(test_client, a)
    bh = _auth(b["token"], b["workspaceId"])

    resp = await test_client.get(f"/api/issues/{issue['id']}/vcs/branch-name", headers=bh)
    assert resp.status_code == 404, resp.text

    resp2 = await test_client.post(
        f"/api/issues/{issue['id']}/vcs/links",
        headers=bh,
        json={"kind": "branch", "branchName": "x"},
    )
    assert resp2.status_code == 404, resp2.text
