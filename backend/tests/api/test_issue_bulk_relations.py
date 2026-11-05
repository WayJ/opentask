"""E20：Bulk 扩展（cycle/tags + 租户）与列表 blocks/blocked_by 计数"""
import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e20"):
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


async def _create_cycle(client: AsyncClient, user: dict, name: str = "C1") -> dict:
    from datetime import datetime, timedelta, timezone

    start = datetime.now(timezone.utc).replace(tzinfo=None)
    end = start + timedelta(days=14)
    resp = await client.post(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "name": name,
            "starts_at": start.isoformat(),
            "ends_at": end.isoformat(),
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_tag(client: AsyncClient, user: dict, name: str) -> dict:
    resp = await client.post(
        "/api/tags",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name, "color": "#5e6ad2"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_bulk_update_status_priority_assignee(test_client: AsyncClient):
    user = await _register(test_client, "bu")
    a = await _create_issue(test_client, user, "bulk-a")
    b = await _create_issue(test_client, user, "bulk-b")

    resp = await test_client.post(
        "/api/issues/bulk/update",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "issue_ids": [a["id"], b["id"]],
            "status": "in_progress",
            "priority": "high",
            "assignee_id": user["userId"],
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["affected_rows"] == 2

    for iid in (a["id"], b["id"]):
        got = await test_client.get(
            f"/api/issues/{iid}",
            headers=_auth(user["token"], user["workspaceId"]),
        )
        assert got.status_code == 200
        body = got.json()["data"]
        assert body["status"] == "in_progress"
        assert body["priority"] == "high"
        assert body["assignee_id"] == user["userId"]


@pytest.mark.asyncio
async def test_bulk_update_cycle_and_tags(test_client: AsyncClient):
    user = await _register(test_client, "bc")
    issue = await _create_issue(test_client, user, "bulk-cycle")
    cycle = await _create_cycle(test_client, user, "BulkCycle")
    tag = await _create_tag(test_client, user, f"t-{uuid.uuid4().hex[:6]}")
    tag_id = tag.get("id") or tag.get("tagId")

    resp = await test_client.post(
        "/api/issues/bulk/update",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "issue_ids": [issue["id"]],
            "cycle_id": cycle["id"],
            "tag_ids": [tag_id],
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["affected_rows"] >= 1

    got = await test_client.get(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.status_code == 200, got.text
    body = got.json()["data"]
    assert body.get("cycle_id") == cycle["id"]
    tags = body.get("tags") or []
    assert any(str(t.get("id")) == str(tag_id) for t in tags)


@pytest.mark.asyncio
async def test_bulk_update_rejects_cross_tenant(test_client: AsyncClient):
    owner = await _register(test_client, "bxo")
    stranger = await _register(test_client, "bxs")
    issue = await _create_issue(test_client, owner, "secret-bulk")

    resp = await test_client.post(
        "/api/issues/bulk/update",
        headers=_auth(stranger["token"], stranger["workspaceId"]),
        json={"issue_ids": [issue["id"]], "status": "closed"},
    )
    # 无本 WS 可更新目标 → 403
    assert resp.status_code == 403, resp.text

    got = await test_client.get(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert got.json()["data"]["status"] == "open"


@pytest.mark.asyncio
async def test_bulk_requires_workspace_header(test_client: AsyncClient):
    user = await _register(test_client, "bh")
    issue = await _create_issue(test_client, user, "need-header")
    resp = await test_client.post(
        "/api/issues/bulk/update",
        headers={"Authorization": f"Bearer {user['token']}"},
        json={"issue_ids": [issue["id"]], "priority": "low"},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_list_exposes_blocks_counts(test_client: AsyncClient):
    user = await _register(test_client, "rel")
    blocker = await _create_issue(test_client, user, "blocker")
    blocked = await _create_issue(test_client, user, "blocked")

    add = await test_client.post(
        f"/api/issues/{blocker['id']}/relations",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"target_id": blocked["id"], "relation_type": "blocks"},
    )
    assert add.status_code == 200, add.text

    listed = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"page_size": 50},
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]["rows"]
    by_id = {r["id"]: r for r in rows}
    assert by_id[blocker["id"]].get("blocks_count", 0) >= 1
    assert by_id[blocked["id"]].get("blocked_by_count", 0) >= 1


@pytest.mark.asyncio
async def test_relation_crud_same_workspace(test_client: AsyncClient):
    user = await _register(test_client, "rc")
    a = await _create_issue(test_client, user, "rel-a")
    b = await _create_issue(test_client, user, "rel-b")

    add = await test_client.post(
        f"/api/issues/{a['id']}/relations",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"target_id": b["id"], "relation_type": "relates_to"},
    )
    assert add.status_code == 200, add.text

    listed = await test_client.get(
        f"/api/issues/{a['id']}/relations",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert listed.status_code == 200
    src = listed.json()["data"]["as_source"]
    assert any(r["target_id"] == b["id"] for r in src)

    removed = await test_client.delete(
        f"/api/issues/{a['id']}/relations",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"target_id": b["id"], "relation_type": "relates_to"},
    )
    assert removed.status_code == 200, removed.text
