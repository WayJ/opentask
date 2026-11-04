"""E7-S1：Workspace Labels (tags/tag_groups) CRUD + Issue 打标 + 租户隔离"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from opentask.api.tasks.service import get_or_create_tag
from opentask.models.tag.model import Tag
from opentask.repositories.base import SessionCreator


async def _register(client: AsyncClient, prefix: str = "tg"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str):
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
async def test_create_and_list_tags(test_client: AsyncClient):
    user = await _register(test_client, "tg_c")
    create = await test_client.post(
        "/api/tags",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "bug", "color": "#ef4444"},
    )
    assert create.status_code == 200, create.text
    body = create.json()["data"]
    assert body["name"] == "bug"
    assert body["color"] == "#ef4444"
    assert body["workspaceId"] == user["workspaceId"]
    assert body["groupId"] is None
    tag_id = body["id"]

    listed = await test_client.get(
        "/api/tags",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]["rows"]
    assert any(r["id"] == tag_id for r in rows)

    one = await test_client.get(
        f"/api/tags/{tag_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert one.status_code == 200, one.text
    assert one.json()["data"]["id"] == tag_id

    default_color = await test_client.post(
        "/api/tags",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "plain"},
    )
    assert default_color.status_code == 200, default_color.text
    assert default_color.json()["data"]["color"] == "#3b82f6"


@pytest.mark.asyncio
async def test_tags_cross_workspace_isolation(test_client: AsyncClient):
    a = await _register(test_client, "tg_a")
    b = await _register(test_client, "tg_b")
    created = await test_client.post(
        "/api/tags",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"name": "secret"},
    )
    assert created.status_code == 200, created.text
    tag_id = created.json()["data"]["id"]

    forbidden_list = await test_client.get(
        "/api/tags",
        headers=_auth(b["token"], a["workspaceId"]),
    )
    assert forbidden_list.status_code == 403

    missing = await test_client.get(
        f"/api/tags/{tag_id}",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert missing.status_code == 404

    b_list = await test_client.get(
        "/api/tags",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert b_list.status_code == 200
    assert all(r["id"] != tag_id for r in b_list.json()["data"]["rows"])


@pytest.mark.asyncio
async def test_duplicate_name_same_workspace_409(test_client: AsyncClient):
    user = await _register(test_client, "tg_dup")
    first = await test_client.post(
        "/api/tags",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "dup"},
    )
    assert first.status_code == 200, first.text
    second = await test_client.post(
        "/api/tags",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "dup"},
    )
    assert second.status_code == 409, second.text


@pytest.mark.asyncio
async def test_create_tag_group_and_assign(test_client: AsyncClient):
    user = await _register(test_client, "tg_g")
    group = await test_client.post(
        "/api/tag-groups",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "Area", "color": "#22c55e"},
    )
    assert group.status_code == 200, group.text
    g = group.json()["data"]
    assert g["name"] == "Area"
    assert g["workspaceId"] == user["workspaceId"]
    group_id = g["id"]

    tag = await test_client.post(
        "/api/tags",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "frontend", "group_id": group_id},
    )
    assert tag.status_code == 200, tag.text
    assert tag.json()["data"]["groupId"] == group_id

    listed = await test_client.get(
        "/api/tags",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"group_id": group_id},
    )
    assert listed.status_code == 200
    assert any(r["name"] == "frontend" for r in listed.json()["data"]["rows"])


@pytest.mark.asyncio
async def test_patch_tag_name_color_group(test_client: AsyncClient):
    user = await _register(test_client, "tg_p")
    group = await test_client.post(
        "/api/tag-groups",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "G1"},
    )
    group_id = group.json()["data"]["id"]
    tag = await test_client.post(
        "/api/tags",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "old"},
    )
    tag_id = tag.json()["data"]["id"]

    patched = await test_client.patch(
        f"/api/tags/{tag_id}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "new", "color": "#111111", "group_id": group_id},
    )
    assert patched.status_code == 200, patched.text
    data = patched.json()["data"]
    assert data["name"] == "new"
    assert data["color"] == "#111111"
    assert data["groupId"] == group_id


@pytest.mark.asyncio
async def test_delete_tag_cascades_issue_tags(test_client: AsyncClient):
    user = await _register(test_client, "tg_del")
    tag = await test_client.post(
        "/api/tags",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "temp"},
    )
    tag_id = tag.json()["data"]["id"]
    issue = await _create_issue(test_client, user, "tagged")
    attach = await test_client.post(
        f"/api/issues/{issue['id']}/tags/{tag_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert attach.status_code == 200, attach.text

    deleted = await test_client.delete(
        f"/api/tags/{tag_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert deleted.status_code == 200, deleted.text

    tags = await test_client.get(
        f"/api/issues/{issue['id']}/tags",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert tags.status_code == 200
    assert tags.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_issue_get_tags_not_empty_after_attach(test_client: AsyncClient):
    user = await _register(test_client, "tg_iss")
    tag = await test_client.post(
        "/api/tags",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": "alpha", "color": "#abc123"},
    )
    tag_id = tag.json()["data"]["id"]
    issue = await _create_issue(test_client, user, "has-tag")

    empty = await test_client.get(
        f"/api/issues/{issue['id']}/tags",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert empty.status_code == 200
    assert empty.json()["data"]["total"] == 0

    await test_client.post(
        f"/api/issues/{issue['id']}/tags/{tag_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    got = await test_client.get(
        f"/api/issues/{issue['id']}/tags",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.status_code == 200, got.text
    rows = got.json()["data"]["rows"]
    assert got.json()["data"]["total"] == 1
    assert rows[0]["id"] == tag_id
    assert rows[0]["name"] == "alpha"
    assert rows[0]["color"] == "#abc123"

    # list issue includes tags for groupBy
    listed = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"search": "has-tag"},
    )
    assert listed.status_code == 200
    issue_row = next(r for r in listed.json()["data"]["rows"] if r["id"] == issue["id"])
    assert any(t["id"] == tag_id for t in (issue_row.get("tags") or []))


@pytest.mark.asyncio
async def test_issue_put_replace_tags(test_client: AsyncClient):
    user = await _register(test_client, "tg_put")
    t1 = (
        await test_client.post(
            "/api/tags",
            headers=_auth(user["token"], user["workspaceId"]),
            json={"name": "t1"},
        )
    ).json()["data"]["id"]
    t2 = (
        await test_client.post(
            "/api/tags",
            headers=_auth(user["token"], user["workspaceId"]),
            json={"name": "t2"},
        )
    ).json()["data"]["id"]
    t3 = (
        await test_client.post(
            "/api/tags",
            headers=_auth(user["token"], user["workspaceId"]),
            json={"name": "t3"},
        )
    ).json()["data"]["id"]
    issue = await _create_issue(test_client, user, "replace-me")
    await test_client.post(
        f"/api/issues/{issue['id']}/tags/{t1}",
        headers=_auth(user["token"], user["workspaceId"]),
    )

    replaced = await test_client.put(
        f"/api/issues/{issue['id']}/tags",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"tag_ids": [t2, t3]},
    )
    assert replaced.status_code == 200, replaced.text
    rows = replaced.json()["data"]["rows"]
    ids = sorted(r["id"] for r in rows)
    assert ids == sorted([t2, t3])


@pytest.mark.asyncio
async def test_viewer_cannot_create_tag(test_client: AsyncClient):
    owner = await _register(test_client, "tg_own")
    viewer = await _register(test_client, "tg_view")
    await _add_member(test_client, owner, viewer, role="viewer")

    denied = await test_client.post(
        "/api/tags",
        headers=_auth(viewer["token"], owner["workspaceId"]),
        json={"name": "nope"},
    )
    assert denied.status_code == 403

    # owner creates; viewer can list
    await test_client.post(
        "/api/tags",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"name": "ok"},
    )
    listed = await test_client.get(
        "/api/tags",
        headers=_auth(viewer["token"], owner["workspaceId"]),
    )
    assert listed.status_code == 200
    assert any(r["name"] == "ok" for r in listed.json()["data"]["rows"])


@pytest.mark.asyncio
async def test_tags_require_workspace_header(test_client: AsyncClient):
    user = await _register(test_client, "tg_hdr")
    missing = await test_client.get(
        "/api/tags",
        headers=_auth(user["token"]),
    )
    assert missing.status_code == 400


@pytest.mark.asyncio
async def test_get_or_create_tag_scoped_to_workspace(test_client: AsyncClient):
    a = await _register(test_client, "tg_goc_a")
    b = await _register(test_client, "tg_goc_b")
    # ensure same name can exist in both workspaces via helper
    async with SessionCreator() as session:
        t1 = await get_or_create_tag(session, "shared-name", workspace_id=a["workspaceId"])
        await session.commit()
        id1 = t1.id
    async with SessionCreator() as session:
        t2 = await get_or_create_tag(session, "shared-name", workspace_id=b["workspaceId"])
        await session.commit()
        id2 = t2.id
        again = await get_or_create_tag(session, "shared-name", workspace_id=a["workspaceId"])
        assert again.id == id1
    assert id1 != id2

    async with SessionCreator() as session:
        rows = list(
            (
                await session.execute(select(Tag).where(Tag.name == "shared-name"))
            ).scalars().all()
        )
        assert len(rows) == 2
        assert {r.workspace_id for r in rows} == {a["workspaceId"], b["workspaceId"]}
