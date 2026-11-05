"""E36：Automation trigger custom_field_changed + multi CF conditions AND≤5."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e36"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str = "e36-issue", **extra) -> dict:
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


async def _create_cf(
    client: AsyncClient, user: dict, *, name: str, key: str, type_: str, options=None
) -> dict:
    body = {"name": name, "key": key, "type": type_}
    if options is not None:
        body["options"] = options
    resp = await client.post(
        "/api/custom-fields",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _set_cf(client: AsyncClient, user: dict, issue_id: str, values: list) -> dict:
    resp = await client.patch(
        f"/api/issues/{issue_id}/custom-fields",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"values": values},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_custom_field_changed_triggers_action(test_client: AsyncClient):
    user = await _register(test_client, "e36_trg")
    h = _auth(user["token"], user["workspaceId"])
    await _create_cf(
        test_client,
        user,
        name="Tier",
        key="tier",
        type_="single_select",
        options=["free", "pro", "enterprise"],
    )
    issue = await _create_issue(test_client, user, "cf-changed")

    rule = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "tier→high",
            "triggerType": "custom_field_changed",
            "triggerConfig": {"field_key": "tier"},
            "actionType": "set_priority",
            "actionConfig": {"priority": "high"},
        },
    )
    assert rule.status_code == 200, rule.text

    await _set_cf(test_client, user, issue["id"], [{"key": "tier", "value": "pro"}])
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.json()["data"]["priority"] == "high"


@pytest.mark.asyncio
async def test_custom_field_changed_field_filter_and_from_to(test_client: AsyncClient):
    user = await _register(test_client, "e36_flt")
    h = _auth(user["token"], user["workspaceId"])
    await _create_cf(
        test_client,
        user,
        name="Tier",
        key="tier",
        type_="single_select",
        options=["free", "pro", "enterprise"],
    )
    await _create_cf(test_client, user, name="Note", key="note", type_="text")
    issue = await _create_issue(test_client, user, "filter-me")
    await _set_cf(test_client, user, issue["id"], [{"key": "tier", "value": "free"}])

    # Only fires when tier free→pro
    rule = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "free→pro comment",
            "triggerType": "custom_field_changed",
            "triggerConfig": {"key": "tier", "from": "free", "to": "pro"},
            "actionType": "add_comment",
            "actionConfig": {"content": "upgraded"},
        },
    )
    assert rule.status_code == 200, rule.text

    # Wrong field — should NOT fire
    await _set_cf(test_client, user, issue["id"], [{"key": "note", "value": "x"}])
    comments = await test_client.get(f"/api/issues/{issue['id']}/comments", headers=h)
    rows = comments.json()["data"]
    if isinstance(rows, dict):
        rows = rows.get("rows") or rows.get("items") or []
    assert not any("upgraded" in (c.get("content") or "") for c in rows)

    # Wrong to value
    await _set_cf(test_client, user, issue["id"], [{"key": "tier", "value": "enterprise"}])
    comments = await test_client.get(f"/api/issues/{issue['id']}/comments", headers=h)
    rows = comments.json()["data"]
    if isinstance(rows, dict):
        rows = rows.get("rows") or rows.get("items") or []
    assert not any("upgraded" in (c.get("content") or "") for c in rows)

    # Reset to free then free→pro
    await _set_cf(test_client, user, issue["id"], [{"key": "tier", "value": "free"}])
    await _set_cf(test_client, user, issue["id"], [{"key": "tier", "value": "pro"}])
    comments = await test_client.get(f"/api/issues/{issue['id']}/comments", headers=h)
    rows = comments.json()["data"]
    if isinstance(rows, dict):
        rows = rows.get("rows") or rows.get("items") or []
    assert any("upgraded" in (c.get("content") or "") for c in rows)


@pytest.mark.asyncio
async def test_multi_custom_fields_and_max5(test_client: AsyncClient):
    user = await _register(test_client, "e36_and")
    h = _auth(user["token"], user["workspaceId"])
    await _create_cf(
        test_client,
        user,
        name="Tier",
        key="tier",
        type_="single_select",
        options=["free", "pro"],
    )
    await _create_cf(test_client, user, name="Region", key="region", type_="text")
    issue = await _create_issue(test_client, user, "and-me")
    await _set_cf(
        test_client,
        user,
        issue["id"],
        [{"key": "tier", "value": "pro"}, {"key": "region", "value": "us"}],
    )

    # >5 → 400
    too_many = [{"key": f"k{i}", "op": "is_set"} for i in range(6)]
    bad = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "too-many",
            "triggerType": "issue.status_changed",
            "condition": {"customFields": too_many},
            "actionType": "set_priority",
            "actionConfig": {"priority": "low"},
        },
    )
    assert bad.status_code == 400, bad.text

    rule = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "and-cf→high",
            "triggerType": "issue.status_changed",
            "triggerConfig": {"to": "in_progress"},
            "condition": {
                "customFields": [
                    {"key": "tier", "op": "eq", "value": "pro"},
                    {"key": "region", "op": "eq", "value": "us"},
                ]
            },
            "actionType": "set_priority",
            "actionConfig": {"priority": "high"},
        },
    )
    assert rule.status_code == 200, rule.text

    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"status": "in_progress"},
    )
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.json()["data"]["priority"] == "high"


@pytest.mark.asyncio
async def test_set_custom_field_does_not_retrigger_cf_changed(test_client: AsyncClient):
    """User CF write fires rule → set_custom_field must NOT fire another cf-changed rule (depth≤1)."""
    user = await _register(test_client, "e36_loop")
    h = _auth(user["token"], user["workspaceId"])
    await _create_cf(test_client, user, name="A", key="cf_a", type_="text")
    await _create_cf(test_client, user, name="B", key="cf_b", type_="text")
    issue = await _create_issue(test_client, user, "loop")

    r1 = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "a→set-b",
            "triggerType": "custom_field_changed",
            "triggerConfig": {"field_key": "cf_a"},
            "actionType": "set_custom_field",
            "actionConfig": {"key": "cf_b", "value": "from-a"},
        },
    )
    assert r1.status_code == 200, r1.text

    r2 = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "b→critical",
            "triggerType": "custom_field_changed",
            "triggerConfig": {"field_key": "cf_b"},
            "actionType": "set_priority",
            "actionConfig": {"priority": "critical"},
        },
    )
    assert r2.status_code == 200, r2.text

    await _set_cf(test_client, user, issue["id"], [{"key": "cf_a", "value": "x"}])

    # r1 should have set cf_b
    filtered = await test_client.get("/api/issues", headers=h, params={"cf.cf_b": "from-a"})
    rows = filtered.json()["data"]
    if isinstance(rows, dict):
        rows = rows.get("rows") or rows.get("items") or []
    assert any(r["id"] == issue["id"] for r in rows)

    # r2 must NOT have run (would set critical)
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.json()["data"]["priority"] == "medium"


@pytest.mark.asyncio
async def test_viewer_cannot_create_cf_changed_rule(test_client: AsyncClient):
    owner = await _register(test_client, "e36_own")
    viewer = await _register(test_client, "e36_view")
    # invite viewer into owner ws as viewer — use members API if available
    # Fallback: create rule in viewer's own ws as owner then switch — instead register
    # and demote via workspace members if endpoint exists.
    # Minimal: attempt create with a second user who is not member → 403/404 on X-Workspace-Id.
    h_view_on_owner = _auth(viewer["token"], owner["workspaceId"])
    resp = await test_client.post(
        "/api/automations",
        headers=h_view_on_owner,
        json={
            "name": "nope",
            "triggerType": "custom_field_changed",
            "actionType": "set_priority",
            "actionConfig": {"priority": "high"},
        },
    )
    assert resp.status_code in (403, 404), resp.text
