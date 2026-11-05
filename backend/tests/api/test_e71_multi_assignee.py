"""E71: multi-assignee mid — junction, filters, notify fanout, webhook reuse."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e71"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/auth/register",
        json={"userName": uname, "password": "Passw0rd!", "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    h = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        h["X-Workspace-Id"] = workspace_id
    return h


async def _add_member(client: AsyncClient, owner: dict, member: dict):
    resp = await client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": "member"},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_create_with_assignee_ids_mirrors_primary(test_client: AsyncClient):
    owner = await _register(test_client, "e71_c")
    a = await _register(test_client, "e71_a")
    b = await _register(test_client, "e71_b")
    await _add_member(test_client, owner, a)
    await _add_member(test_client, owner, b)
    h = _auth(owner["token"], owner["workspaceId"])

    resp = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "multi create",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "assignee_ids": [a["userId"], b["userId"]],
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["assignee_id"] == a["userId"]
    ids = [u["id"] for u in data.get("assignees") or []]
    assert ids == [a["userId"], b["userId"]]


@pytest.mark.asyncio
async def test_patch_assignee_ids_replaces(test_client: AsyncClient):
    owner = await _register(test_client, "e71_p")
    a = await _register(test_client, "e71_pa")
    b = await _register(test_client, "e71_pb")
    await _add_member(test_client, owner, a)
    await _add_member(test_client, owner, b)
    h = _auth(owner["token"], owner["workspaceId"])

    created = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "replace",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "assignee_ids": [a["userId"], b["userId"]],
        },
    )
    issue_id = created.json()["data"]["id"]

    patched = await test_client.put(
        f"/api/issues/{issue_id}",
        headers=h,
        json={"assignee_ids": [b["userId"]]},
    )
    assert patched.status_code == 200, patched.text
    data = patched.json()["data"]
    assert data["assignee_id"] == b["userId"]
    assert [u["id"] for u in data.get("assignees") or []] == [b["userId"]]


@pytest.mark.asyncio
async def test_patch_assignee_id_only_clears_collaborators(test_client: AsyncClient):
    owner = await _register(test_client, "e71_q2")
    a = await _register(test_client, "e71_q2a")
    b = await _register(test_client, "e71_q2b")
    c = await _register(test_client, "e71_q2c")
    for m in (a, b, c):
        await _add_member(test_client, owner, m)
    h = _auth(owner["token"], owner["workspaceId"])

    created = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "q2a clear",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "assignee_ids": [a["userId"], b["userId"]],
        },
    )
    issue_id = created.json()["data"]["id"]

    patched = await test_client.put(
        f"/api/issues/{issue_id}",
        headers=h,
        json={"assignee_id": c["userId"]},
    )
    assert patched.status_code == 200, patched.text
    data = patched.json()["data"]
    assert data["assignee_id"] == c["userId"]
    assert [u["id"] for u in data.get("assignees") or []] == [c["userId"]]


@pytest.mark.asyncio
async def test_max_11_returns_400(test_client: AsyncClient):
    owner = await _register(test_client, "e71_max")
    members = []
    for i in range(11):
        m = await _register(test_client, f"e71_m{i}")
        await _add_member(test_client, owner, m)
        members.append(m)
    h = _auth(owner["token"], owner["workspaceId"])
    resp = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "too many",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "assignee_ids": [m["userId"] for m in members],
        },
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_assignee_filters_primary_vs_any(test_client: AsyncClient):
    owner = await _register(test_client, "e71_f")
    a = await _register(test_client, "e71_fa")
    b = await _register(test_client, "e71_fb")
    await _add_member(test_client, owner, a)
    await _add_member(test_client, owner, b)
    h = _auth(owner["token"], owner["workspaceId"])

    # primary a, collab b
    r1 = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "primary-a",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "assignee_ids": [a["userId"], b["userId"]],
        },
    )
    id_primary_a = r1.json()["data"]["id"]

    # primary b, collab a  → a is collaborator only
    r2 = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "collab-a",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "assignee_ids": [b["userId"], a["userId"]],
        },
    )
    id_collab_a = r2.json()["data"]["id"]

    primary = await test_client.get(
        "/api/issues",
        headers=h,
        params={"assignee_id": a["userId"], "pageSize": 50},
    )
    assert primary.status_code == 200, primary.text
    pids = {row["id"] for row in primary.json()["data"]["rows"]}
    assert id_primary_a in pids
    assert id_collab_a not in pids

    any_f = await test_client.get(
        "/api/issues",
        headers=h,
        params={"assignee_any": a["userId"], "pageSize": 50},
    )
    assert any_f.status_code == 200, any_f.text
    aids = {row["id"] for row in any_f.json()["data"]["rows"]}
    assert id_primary_a in aids
    assert id_collab_a in aids


@pytest.mark.asyncio
async def test_non_member_assignee_400(test_client: AsyncClient):
    owner = await _register(test_client, "e71_nm")
    outsider = await _register(test_client, "e71_out")
    h = _auth(owner["token"], owner["workspaceId"])
    resp = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "bad member",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "assignee_ids": [outsider["userId"]],
        },
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_webhook_reuses_assignee_changed_payload_has_ids(test_client: AsyncClient):
    owner = await _register(test_client, "e71_wh")
    a = await _register(test_client, "e71_wha")
    b = await _register(test_client, "e71_whb")
    await _add_member(test_client, owner, a)
    await _add_member(test_client, owner, b)
    h = _auth(owner["token"], owner["workspaceId"])

    created = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "wh",
            "type": "feature",
            "status": "open",
            "priority": "medium",
        },
    )
    issue_id = created.json()["data"]["id"]

    with patch(
        "opentask.services.workspace_webhook.service.WorkspaceWebhookService.dispatch_event",
        new_callable=AsyncMock,
    ) as dispatch:
        await test_client.post(
            "/api/webhooks",
            headers=h,
            json={
                "url": "https://example.com/e71",
                "events": ["issue.updated", "issue.assignee_changed"],
            },
        )
        patched = await test_client.put(
            f"/api/issues/{issue_id}",
            headers=h,
            json={"assignee_ids": [a["userId"], b["userId"]]},
        )
        assert patched.status_code == 200, patched.text

        types = [c.kwargs.get("event_type") for c in dispatch.await_args_list]
        assert "issue.assignee_changed" in types
        assert "issue.assignees_changed" not in types
        asg = next(
            c
            for c in dispatch.await_args_list
            if c.kwargs.get("event_type") == "issue.assignee_changed"
        )
        data = asg.kwargs.get("data") or {}
        assert data.get("to") == a["userId"]
        assert data.get("assignee_ids") == [a["userId"], b["userId"]]


@pytest.mark.asyncio
async def test_notify_fanout_new_assignees(test_client: AsyncClient):
    owner = await _register(test_client, "e71_nf")
    a = await _register(test_client, "e71_nfa")
    b = await _register(test_client, "e71_nfb")
    await _add_member(test_client, owner, a)
    await _add_member(test_client, owner, b)
    h = _auth(owner["token"], owner["workspaceId"])

    created = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "notify",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "assignee_ids": [a["userId"]],
        },
    )
    issue_id = created.json()["data"]["id"]

    # Clear a's inbox noise from create if any, then add b
    await test_client.put(
        f"/api/issues/{issue_id}",
        headers=h,
        json={"assignee_ids": [a["userId"], b["userId"]]},
    )

    inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(b["token"], owner["workspaceId"]),
        params={"page": 1, "page_size": 50},
    )
    assert inbox.status_code == 200, inbox.text
    rows = inbox.json()["data"]["rows"]
    assigned = [
        r
        for r in rows
        if r.get("type") == "assigned" and r.get("resourceId") == issue_id
    ]
    assert assigned, f"expected assigned notification for b; got {rows[:5]}"
