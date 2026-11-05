"""E81: Project milestones issue_count + status filter + SET NULL delete."""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e81"):
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
        json={"name": name or f"E81-{uuid.uuid4().hex[:6]}", "description": "e81"},
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
async def test_create_list_get_include_issue_count_zero(test_client: AsyncClient):
    user = await _register(test_client, "e81c")
    project = await _create_project(test_client, user)
    created = await _create_milestone(test_client, user, project["id"], name="Alpha")
    assert "issue_count" in created
    assert created["issue_count"] == 0

    listed = await test_client.get(
        f"/api/projects/{project['id']}/milestones",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    rows = _rows(listed.json()["data"])
    row = next(r for r in rows if r["id"] == created["id"])
    assert row["issue_count"] == 0

    one = await test_client.get(
        f"/api/projects/{project['id']}/milestones/{created['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert one.status_code == 200, one.text
    assert one.json()["data"]["issue_count"] == 0


@pytest.mark.asyncio
async def test_issue_count_two_and_update_preserves_count(test_client: AsyncClient):
    user = await _register(test_client, "e81n")
    project = await _create_project(test_client, user)
    ms = await _create_milestone(test_client, user, project["id"], name="Ship")
    await _create_issue(
        test_client, user, "i1", project_id=project["id"], milestone_id=ms["id"]
    )
    await _create_issue(
        test_client, user, "i2", project_id=project["id"], milestone_id=ms["id"]
    )

    listed = await test_client.get(
        f"/api/projects/{project['id']}/milestones",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    row = next(r for r in _rows(listed.json()["data"]) if r["id"] == ms["id"])
    assert row["issue_count"] == 2

    one = await test_client.get(
        f"/api/projects/{project['id']}/milestones/{ms['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert one.json()["data"]["issue_count"] == 2

    patched = await test_client.patch(
        f"/api/projects/{project['id']}/milestones/{ms['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "Ship-v2"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["name"] == "Ship-v2"
    assert patched.json()["data"]["issue_count"] == 2


@pytest.mark.asyncio
async def test_list_status_filter(test_client: AsyncClient):
    user = await _register(test_client, "e81s")
    project = await _create_project(test_client, user)
    planned = await _create_milestone(
        test_client, user, project["id"], name="P", status="planned"
    )
    done = await _create_milestone(
        test_client, user, project["id"], name="D", status="done"
    )

    only_done = await test_client.get(
        f"/api/projects/{project['id']}/milestones",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"status": "done"},
    )
    assert only_done.status_code == 200, only_done.text
    ids = {r["id"] for r in _rows(only_done.json()["data"])}
    assert done["id"] in ids
    assert planned["id"] not in ids

    only_planned = await test_client.get(
        f"/api/projects/{project['id']}/milestones",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"status": "planned"},
    )
    ids_p = {r["id"] for r in _rows(only_planned.json()["data"])}
    assert planned["id"] in ids_p
    assert done["id"] not in ids_p

    bad = await test_client.get(
        f"/api/projects/{project['id']}/milestones",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"status": "bogus"},
    )
    assert bad.status_code == 400, bad.text


@pytest.mark.asyncio
async def test_delete_sets_issue_milestone_null(test_client: AsyncClient):
    user = await _register(test_client, "e81d")
    project = await _create_project(test_client, user)
    ms = await _create_milestone(test_client, user, project["id"], name="Gone")
    i1 = await _create_issue(
        test_client, user, "a", project_id=project["id"], milestone_id=ms["id"]
    )
    i2 = await _create_issue(
        test_client, user, "b", project_id=project["id"], milestone_id=ms["id"]
    )

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

    for issue_id in (i1["id"], i2["id"]):
        got = await test_client.get(
            f"/api/issues/{issue_id}",
            headers=_auth(user["token"], user["workspaceId"]),
        )
        assert got.status_code == 200, got.text
        assert got.json()["data"].get("milestone_id") in (None, "")


@pytest.mark.asyncio
async def test_cross_project_404_and_viewer_403(test_client: AsyncClient):
    owner = await _register(test_client, "e81o")
    viewer = await _register(test_client, "e81v")
    await _add_member(test_client, owner, viewer, role="viewer")
    p1 = await _create_project(test_client, owner, name="P1")
    p2 = await _create_project(test_client, owner, name="P2")
    ms = await _create_milestone(test_client, owner, p1["id"], name="OnlyP1")

    cross = await test_client.get(
        f"/api/projects/{p2['id']}/milestones/{ms['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert cross.status_code == 404, cross.text

    forbidden = await test_client.post(
        f"/api/projects/{p1['id']}/milestones",
        headers=_auth(viewer["token"], owner["workspaceId"]),
        json={"name": "Nope"},
    )
    assert forbidden.status_code == 403, forbidden.text


@pytest.mark.asyncio
async def test_cross_workspace_isolation(test_client: AsyncClient):
    a = await _register(test_client, "e81a")
    b = await _register(test_client, "e81b")
    project = await _create_project(test_client, a)
    ms = await _create_milestone(test_client, a, project["id"], name="Secret")

    forbidden = await test_client.get(
        f"/api/projects/{project['id']}/milestones/{ms['id']}",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert forbidden.status_code in (403, 404), forbidden.text


def test_e80_helper_file_untouched():
    """E81 must not change apply_project_move_integrity / milestone_for_duplicate."""
    root = Path(__file__).resolve().parents[2]
    path = root / "opentask" / "services" / "issue_project_move.py"
    text = path.read_text(encoding="utf-8")
    assert "def apply_project_move_integrity" in text
    assert "def milestone_for_duplicate" in text
    # Sanity: no E81 markers stuffed into the helper
    assert "issue_count" not in text
    assert "E81" not in text
