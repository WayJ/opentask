"""E8-S1：Project milestones CRUD + project dates + issue.milestone_id"""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "ms"):
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


async def _create_project(client: AsyncClient, user: dict, name: str | None = None) -> dict:
    resp = await client.post(
        "/api/projects",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name or f"Proj-{uuid.uuid4().hex[:6]}", "description": "ms"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_milestone(
    client: AsyncClient,
    user: dict,
    project_id: str,
    name: str = "M1",
    **extra,
) -> dict:
    body = {"name": name, **extra}
    resp = await client.post(
        f"/api/projects/{project_id}/milestones",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_issue(client: AsyncClient, user: dict, title: str, **extra):
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


def _rows(payload):
    data = payload if not isinstance(payload, dict) else payload
    if isinstance(data, list):
        return data
    return data.get("rows") or data.get("items") or []


@pytest.mark.asyncio
async def test_create_and_list_milestones(test_client: AsyncClient):
    user = await _register(test_client, "ms_c")
    project = await _create_project(test_client, user)
    created = await _create_milestone(
        test_client,
        user,
        project["id"],
        name="Alpha",
        target_date=datetime(2026, 12, 1).isoformat(),
        status="planned",
    )
    assert created["name"] == "Alpha"
    assert created["project_id"] == project["id"]
    assert created["workspace_id"] == user["workspaceId"]
    assert created["status"] == "planned"
    assert created.get("target_date")

    listed = await test_client.get(
        f"/api/projects/{project['id']}/milestones",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    rows = _rows(listed.json()["data"])
    assert any(r["id"] == created["id"] for r in rows)

    one = await test_client.get(
        f"/api/projects/{project['id']}/milestones/{created['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert one.status_code == 200, one.text
    assert one.json()["data"]["id"] == created["id"]


@pytest.mark.asyncio
async def test_milestones_cross_workspace_isolation(test_client: AsyncClient):
    a = await _register(test_client, "ms_a")
    b = await _register(test_client, "ms_b")
    project = await _create_project(test_client, a)
    ms = await _create_milestone(test_client, a, project["id"], name="Secret")

    forbidden_list = await test_client.get(
        f"/api/projects/{project['id']}/milestones",
        headers=_auth(b["token"], a["workspaceId"]),
    )
    assert forbidden_list.status_code in (403, 404), forbidden_list.text

    forbidden_get = await test_client.get(
        f"/api/projects/{project['id']}/milestones/{ms['id']}",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert forbidden_get.status_code in (403, 404), forbidden_get.text


@pytest.mark.asyncio
async def test_update_and_delete_milestone(test_client: AsyncClient):
    user = await _register(test_client, "ms_ud")
    project = await _create_project(test_client, user)
    ms = await _create_milestone(test_client, user, project["id"], name="Draft")

    patched = await test_client.patch(
        f"/api/projects/{project['id']}/milestones/{ms['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "Done-ish", "status": "done", "position": 2},
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()["data"]
    assert body["name"] == "Done-ish"
    assert body["status"] == "done"
    assert body["position"] == 2

    deleted = await test_client.delete(
        f"/api/projects/{project['id']}/milestones/{ms['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert deleted.status_code == 200, deleted.text

    gone = await test_client.get(
        f"/api/projects/{project['id']}/milestones/{ms['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert gone.status_code == 404, gone.text


@pytest.mark.asyncio
async def test_patch_project_starts_and_target_date(test_client: AsyncClient):
    user = await _register(test_client, "ms_pd")
    project = await _create_project(test_client, user)
    starts = datetime(2026, 11, 1, 0, 0, 0).isoformat()
    target = datetime(2026, 12, 31, 0, 0, 0).isoformat()

    updated = await test_client.put(
        f"/api/projects/{project['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"starts_at": starts, "target_date": target},
    )
    assert updated.status_code == 200, updated.text
    data = updated.json()["data"]
    assert data.get("starts_at")
    assert data.get("target_date")

    got = await test_client.get(
        f"/api/projects/{project['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.status_code == 200, got.text
    g = got.json()["data"]
    assert g.get("starts_at")
    assert g.get("target_date")


@pytest.mark.asyncio
async def test_create_issue_with_milestone_id(test_client: AsyncClient):
    user = await _register(test_client, "ms_ic")
    project = await _create_project(test_client, user)
    ms = await _create_milestone(test_client, user, project["id"], name="Ship")
    issue = await _create_issue(
        test_client,
        user,
        "with-ms",
        project_id=project["id"],
        milestone_id=ms["id"],
    )
    assert issue["milestone_id"] == ms["id"]

    got = await test_client.get(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.status_code == 200, got.text
    assert got.json()["data"]["milestone_id"] == ms["id"]


@pytest.mark.asyncio
async def test_update_issue_milestone_id_and_clear(test_client: AsyncClient):
    user = await _register(test_client, "ms_iu")
    project = await _create_project(test_client, user)
    ms = await _create_milestone(test_client, user, project["id"])
    issue = await _create_issue(test_client, user, "to-assign", project_id=project["id"])

    patched = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"milestone_id": ms["id"]},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["milestone_id"] == ms["id"]

    cleared = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"milestone_id": None},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["data"].get("milestone_id") in (None, "")


@pytest.mark.asyncio
async def test_list_issues_filter_by_milestone_id(test_client: AsyncClient):
    user = await _register(test_client, "ms_f")
    project = await _create_project(test_client, user)
    m1 = await _create_milestone(test_client, user, project["id"], name="F1")
    m2 = await _create_milestone(test_client, user, project["id"], name="F2")
    i1 = await _create_issue(
        test_client, user, "in-m1", project_id=project["id"], milestone_id=m1["id"]
    )
    await _create_issue(
        test_client, user, "in-m2", project_id=project["id"], milestone_id=m2["id"]
    )

    listed = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"milestone_id": m1["id"], "page_size": 50},
    )
    assert listed.status_code == 200, listed.text
    rows = _rows(listed.json()["data"])
    ids = {r["id"] for r in rows}
    assert i1["id"] in ids
    assert all(r.get("milestone_id") == m1["id"] for r in rows)


@pytest.mark.asyncio
async def test_refuse_milestone_from_other_project(test_client: AsyncClient):
    user = await _register(test_client, "ms_xp")
    p1 = await _create_project(test_client, user, name=f"P1-{uuid.uuid4().hex[:4]}")
    p2 = await _create_project(test_client, user, name=f"P2-{uuid.uuid4().hex[:4]}")
    ms = await _create_milestone(test_client, user, p1["id"], name="Wrong")
    issue = await _create_issue(test_client, user, "on-p2", project_id=p2["id"])

    bad = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"milestone_id": ms["id"]},
    )
    assert bad.status_code in (400, 422), bad.text


@pytest.mark.asyncio
async def test_refuse_milestone_when_issue_has_no_project(test_client: AsyncClient):
    user = await _register(test_client, "ms_np")
    project = await _create_project(test_client, user)
    ms = await _create_milestone(test_client, user, project["id"])
    issue = await _create_issue(test_client, user, "orphan")

    bad = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"milestone_id": ms["id"]},
    )
    assert bad.status_code in (400, 422), bad.text


@pytest.mark.asyncio
async def test_viewer_cannot_create_milestone(test_client: AsyncClient):
    owner = await _register(test_client, "ms_ow")
    viewer = await _register(test_client, "ms_vw")
    await _add_member(test_client, owner, viewer, role="viewer")
    project = await _create_project(test_client, owner)

    create = await test_client.post(
        f"/api/projects/{project['id']}/milestones",
        headers=_auth(viewer["token"], owner["workspaceId"]),
        json={"name": "Nope"},
    )
    assert create.status_code == 403, create.text

    ms = await _create_milestone(test_client, owner, project["id"], name="Readable")
    listed = await test_client.get(
        f"/api/projects/{project['id']}/milestones",
        headers=_auth(viewer["token"], owner["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    rows = _rows(listed.json()["data"])
    assert any(r["id"] == ms["id"] for r in rows)


@pytest.mark.asyncio
async def test_milestones_require_workspace_header(test_client: AsyncClient):
    user = await _register(test_client, "ms_hdr")
    project = await _create_project(test_client, user)
    missing = await test_client.get(
        f"/api/projects/{project['id']}/milestones",
        headers=_auth(user["token"]),
    )
    assert missing.status_code in (400, 422), missing.text


@pytest.mark.asyncio
async def test_delete_milestone_nulls_issue_milestone_id(test_client: AsyncClient):
    user = await _register(test_client, "ms_null")
    project = await _create_project(test_client, user)
    ms = await _create_milestone(test_client, user, project["id"], name="Temp")
    issue = await _create_issue(
        test_client,
        user,
        "linked",
        project_id=project["id"],
        milestone_id=ms["id"],
    )
    assert issue["milestone_id"] == ms["id"]

    deleted = await test_client.delete(
        f"/api/projects/{project['id']}/milestones/{ms['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert deleted.status_code == 200, deleted.text

    got = await test_client.get(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.status_code == 200, got.text
    assert got.json()["data"].get("milestone_id") in (None, "")
