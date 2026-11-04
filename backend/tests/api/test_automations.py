"""E26：Automations CRUD + 触发→动作 + 防环 + 租户."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "au"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str = "au-issue", **extra) -> dict:
    payload = {
        "title": title,
        "type": "feature",
        "status": "open",
        "priority": "medium",
        **extra,
    }
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json=payload,
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
async def test_automation_crud_enable_disable(test_client: AsyncClient):
    user = await _register(test_client, "au_crud")
    h = _auth(user["token"], user["workspaceId"])

    created = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "On create set high",
            "triggerType": "issue.created",
            "actionType": "set_priority",
            "actionConfig": {"priority": "high"},
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["name"] == "On create set high"
    assert row["enabled"] is True
    assert row["triggerType"] == "issue.created"
    rid = row["id"]

    listed = await test_client.get("/api/automations", headers=h)
    assert listed.status_code == 200, listed.text
    assert any(r["id"] == rid for r in listed.json()["data"]["rows"])

    disabled = await test_client.post(f"/api/automations/{rid}/disable", headers=h)
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["data"]["enabled"] is False

    enabled = await test_client.post(f"/api/automations/{rid}/enable", headers=h)
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["data"]["enabled"] is True

    patched = await test_client.patch(
        f"/api/automations/{rid}",
        headers=h,
        json={"name": "Renamed", "position": 3},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["name"] == "Renamed"

    deleted = await test_client.delete(f"/api/automations/{rid}", headers=h)
    assert deleted.status_code == 200, deleted.text
    missing = await test_client.get(f"/api/automations/{rid}", headers=h)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_automation_viewer_forbidden_and_cross_tenant(test_client: AsyncClient):
    owner = await _register(test_client, "au_own")
    viewer = await _register(test_client, "au_view")
    other = await _register(test_client, "au_oth")
    await _add_member(test_client, owner, viewer, role="viewer")

    h_owner = _auth(owner["token"], owner["workspaceId"])
    created = await test_client.post(
        "/api/automations",
        headers=h_owner,
        json={
            "name": "r1",
            "triggerType": "issue.created",
            "actionType": "add_comment",
            "actionConfig": {"content": "hi"},
        },
    )
    assert created.status_code == 200, created.text
    rid = created.json()["data"]["id"]

    h_viewer = _auth(viewer["token"], owner["workspaceId"])
    listed = await test_client.get("/api/automations", headers=h_viewer)
    assert listed.status_code == 200, listed.text

    forbidden = await test_client.post(
        "/api/automations",
        headers=h_viewer,
        json={
            "name": "nope",
            "triggerType": "issue.created",
            "actionType": "set_status",
            "actionConfig": {"status": "closed"},
        },
    )
    assert forbidden.status_code == 403

    # cross tenant: other cannot see owner's rule
    h_other = _auth(other["token"], other["workspaceId"])
    cross = await test_client.get(f"/api/automations/{rid}", headers=h_other)
    assert cross.status_code in (403, 404)

    # other using owner's workspace header without membership
    h_spoof = _auth(other["token"], owner["workspaceId"])
    spoof = await test_client.get("/api/automations", headers=h_spoof)
    assert spoof.status_code in (403, 404)


@pytest.mark.asyncio
async def test_trigger_issue_created_sets_priority(test_client: AsyncClient):
    user = await _register(test_client, "au_crt")
    h = _auth(user["token"], user["workspaceId"])
    rule = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "new→high",
            "triggerType": "issue.created",
            "actionType": "set_priority",
            "actionConfig": {"priority": "high"},
        },
    )
    assert rule.status_code == 200, rule.text

    issue = await _create_issue(test_client, user, "auto-created")
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.status_code == 200, got.text
    assert got.json()["data"]["priority"] == "high"


@pytest.mark.asyncio
async def test_trigger_status_changed_with_condition(test_client: AsyncClient):
    user = await _register(test_client, "au_st")
    h = _auth(user["token"], user["workspaceId"])
    issue = await _create_issue(test_client, user, "status-flow", priority="high")

    rule = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "high+in_progress→comment",
            "triggerType": "issue.status_changed",
            "triggerConfig": {"to": "in_progress"},
            "condition": {"priorityIs": "high"},
            "actionType": "add_comment",
            "actionConfig": {"content": "started high prio"},
        },
    )
    assert rule.status_code == 200, rule.text

    patched = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"status": "in_progress"},
    )
    assert patched.status_code == 200, patched.text

    comments = await test_client.get(
        f"/api/issues/{issue['id']}/comments",
        headers=h,
    )
    assert comments.status_code == 200, comments.text
    rows = comments.json()["data"]
    if isinstance(rows, dict):
        rows = rows.get("rows") or rows.get("items") or []
    texts = [c.get("content", "") for c in rows]
    assert any("[automation]" in t and "started high prio" in t for t in texts)


@pytest.mark.asyncio
async def test_anti_loop_depth(test_client: AsyncClient):
    """A→set_status should not re-fire status_changed rules (depth≤1)."""
    user = await _register(test_client, "au_loop")
    h = _auth(user["token"], user["workspaceId"])

    # Rule 1: on create → set status in_progress
    r1 = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "create→in_progress",
            "triggerType": "issue.created",
            "actionType": "set_status",
            "actionConfig": {"status": "in_progress"},
        },
    )
    assert r1.status_code == 200, r1.text

    # Rule 2: on status→in_progress → set_priority critical (would loop if depth ignored)
    r2 = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "in_progress→critical",
            "triggerType": "issue.status_changed",
            "triggerConfig": {"to": "in_progress"},
            "actionType": "set_priority",
            "actionConfig": {"priority": "critical"},
        },
    )
    assert r2.status_code == 200, r2.text

    issue = await _create_issue(test_client, user, "loop-check")
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    body = got.json()["data"]
    assert body["status"] == "in_progress"
    # depth≤1: rule2 must NOT run as side-effect of rule1's set_status
    assert body["priority"] == "medium"

    # Direct user status change still fires rule2
    await test_client.post(f"/api/automations/{r1.json()['data']['id']}/disable", headers=h)
    issue2 = await _create_issue(test_client, user, "direct-status")
    put = await test_client.put(
        f"/api/issues/{issue2['id']}",
        headers=h,
        json={"status": "in_progress"},
    )
    assert put.status_code == 200, put.text
    got2 = await test_client.get(f"/api/issues/{issue2['id']}", headers=h)
    body2 = got2.json()["data"]
    assert body2["status"] == "in_progress", body2
    assert body2["priority"] == "critical", body2


@pytest.mark.asyncio
async def test_label_added_adds_assignee(test_client: AsyncClient):
    user = await _register(test_client, "au_lbl")
    h = _auth(user["token"], user["workspaceId"])
    tag = await _create_tag(test_client, user, "urgent")
    issue = await _create_issue(test_client, user, "label-me")

    rule = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "urgent→assign me",
            "triggerType": "label_added",
            "triggerConfig": {"tagId": tag["id"]},
            "actionType": "set_assignee",
            "actionConfig": {"assignee_id": user["userId"]},
        },
    )
    assert rule.status_code == 200, rule.text

    attach = await test_client.post(
        f"/api/issues/{issue['id']}/tags/{tag['id']}",
        headers=h,
    )
    assert attach.status_code == 200, attach.text

    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.status_code == 200
    assert got.json()["data"]["assignee_id"] == user["userId"]


@pytest.mark.asyncio
async def test_disabled_rule_does_not_fire(test_client: AsyncClient):
    user = await _register(test_client, "au_off")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "off",
            "triggerType": "issue.created",
            "actionType": "set_priority",
            "actionConfig": {"priority": "critical"},
            "enabled": False,
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["data"]["enabled"] is False

    issue = await _create_issue(test_client, user, "no-auto")
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.json()["data"]["priority"] == "medium"
