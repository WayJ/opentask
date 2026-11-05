"""E33：Automations × Custom Fields — 条件 ops + set_custom_field + 防环."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e33"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str = "e33-issue", **extra) -> dict:
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


async def _create_cf(client: AsyncClient, user: dict, *, name: str, key: str, type_: str, options=None) -> dict:
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
async def test_condition_custom_field_eq_triggers_action(test_client: AsyncClient):
    user = await _register(test_client, "e33_eq")
    h = _auth(user["token"], user["workspaceId"])
    await _create_cf(
        test_client, user, name="Tier", key="tier", type_="single_select", options=["free", "enterprise"]
    )
    issue = await _create_issue(test_client, user, "eq-me")
    await _set_cf(test_client, user, issue["id"], [{"key": "tier", "value": "enterprise"}])

    rule = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "enterprise→high",
            "triggerType": "issue.status_changed",
            "triggerConfig": {"to": "in_progress"},
            "condition": {
                "customField": {"key": "tier", "op": "eq", "value": "enterprise"}
            },
            "actionType": "set_priority",
            "actionConfig": {"priority": "high"},
        },
    )
    assert rule.status_code == 200, rule.text

    patched = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"status": "in_progress"},
    )
    assert patched.status_code == 200, patched.text
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.json()["data"]["priority"] == "high"


@pytest.mark.asyncio
async def test_condition_unknown_field_does_not_match(test_client: AsyncClient):
    user = await _register(test_client, "e33_unk")
    h = _auth(user["token"], user["workspaceId"])
    issue = await _create_issue(test_client, user, "unk-field")

    rule = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "ghost-cf",
            "triggerType": "issue.status_changed",
            "triggerConfig": {"to": "in_progress"},
            "condition": {
                "customField": {"key": "does_not_exist", "op": "eq", "value": "x"}
            },
            "actionType": "set_priority",
            "actionConfig": {"priority": "critical"},
        },
    )
    assert rule.status_code == 200, rule.text

    patched = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"status": "in_progress"},
    )
    assert patched.status_code == 200, patched.text
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.json()["data"]["priority"] == "medium"


@pytest.mark.asyncio
async def test_condition_contains_multi_and_is_set(test_client: AsyncClient):
    user = await _register(test_client, "e33_mul")
    h = _auth(user["token"], user["workspaceId"])
    await _create_cf(
        test_client,
        user,
        name="TagsCF",
        key="tags_cf",
        type_="multi_select",
        options=["a", "b", "c"],
    )
    await _create_cf(test_client, user, name="Note", key="note", type_="text")

    issue = await _create_issue(test_client, user, "multi-me")
    await _set_cf(
        test_client,
        user,
        issue["id"],
        [{"key": "tags_cf", "value": ["a", "c"]}, {"key": "note", "value": "hello"}],
    )

    # contains member
    r1 = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "has-c→comment",
            "triggerType": "issue.status_changed",
            "triggerConfig": {"to": "in_progress"},
            "condition": {
                "customField": {"key": "tags_cf", "op": "contains", "value": "c"}
            },
            "actionType": "add_comment",
            "actionConfig": {"content": "has-c"},
        },
    )
    assert r1.status_code == 200, r1.text

    patched = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"status": "in_progress"},
    )
    assert patched.status_code == 200, patched.text

    comments = await test_client.get(f"/api/issues/{issue['id']}/comments", headers=h)
    rows = comments.json()["data"]
    if isinstance(rows, dict):
        rows = rows.get("rows") or rows.get("items") or []
    texts = [c.get("content", "") for c in rows]
    assert any("has-c" in t for t in texts)

    # is_set on note → set priority when status → closed
    r2 = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "note-set→low",
            "triggerType": "issue.status_changed",
            "triggerConfig": {"to": "closed"},
            "condition": {"customField": {"key": "note", "op": "is_set"}},
            "actionType": "set_priority",
            "actionConfig": {"priority": "low"},
        },
    )
    assert r2.status_code == 200, r2.text
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"status": "closed"},
    )
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.json()["data"]["priority"] == "low"


@pytest.mark.asyncio
async def test_action_set_custom_field_on_create(test_client: AsyncClient):
    user = await _register(test_client, "e33_set")
    h = _auth(user["token"], user["workspaceId"])
    await _create_cf(test_client, user, name="Source", key="source", type_="text")

    rule = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "create→source",
            "triggerType": "issue.created",
            "actionType": "set_custom_field",
            "actionConfig": {"key": "source", "value": "automation"},
        },
    )
    assert rule.status_code == 200, rule.text

    issue = await _create_issue(test_client, user, "set-cf")
    detail = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert detail.status_code == 200, detail.text
    cfs = detail.json()["data"].get("customFields") or detail.json()["data"].get("custom_fields") or []
    # detail may or may not include custom fields by default — patch-get via values endpoint
    vals = await test_client.get(
        f"/api/issues/{issue['id']}",
        headers={**h, "Accept": "application/json"},
        params={"include": "custom_fields"},
    )
    # Prefer dedicated read via patch noop / list include
    body = vals.json()["data"] if vals.status_code == 200 else {}
    cfs = body.get("customFields") or body.get("custom_fields") or cfs
    if not cfs:
        # fallback: set then re-read via patch with empty? use filter list
        listed = await test_client.get(
            "/api/issues",
            headers=h,
            params={"include": "custom_fields", "search": issue.get("issue_code") or issue["id"]},
        )
        # direct value check via another patch get pattern — use cf filter
        filtered = await test_client.get(
            "/api/issues",
            headers=h,
            params={"cf.source": "automation"},
        )
        assert filtered.status_code == 200, filtered.text
        rows = filtered.json()["data"]
        if isinstance(rows, dict):
            rows = rows.get("rows") or rows.get("items") or []
        assert any(r["id"] == issue["id"] for r in rows), filtered.text
    else:
        by_key = {c.get("key"): c.get("value") for c in cfs}
        assert by_key.get("source") == "automation"


@pytest.mark.asyncio
async def test_action_set_custom_field_invalid_value_no_half_write(test_client: AsyncClient):
    user = await _register(test_client, "e33_bad")
    h = _auth(user["token"], user["workspaceId"])
    await _create_cf(
        test_client,
        user,
        name="Tier",
        key="tier",
        type_="single_select",
        options=["free", "pro"],
    )

    rule = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "create→bad-tier",
            "triggerType": "issue.created",
            "actionType": "set_custom_field",
            "actionConfig": {"key": "tier", "value": "not-an-option"},
        },
    )
    assert rule.status_code == 200, rule.text

    issue = await _create_issue(test_client, user, "bad-cf")
    # invalid write must not persist
    filtered = await test_client.get(
        "/api/issues",
        headers=h,
        params={"cf.tier": "not-an-option"},
    )
    assert filtered.status_code == 200
    rows = filtered.json()["data"]
    if isinstance(rows, dict):
        rows = rows.get("rows") or rows.get("items") or []
    assert not any(r["id"] == issue["id"] for r in rows)

    # issue itself still created (main write not rolled back)
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.status_code == 200
    assert got.json()["data"]["title"] == "bad-cf"


@pytest.mark.asyncio
async def test_set_custom_field_anti_loop_with_status_rule(test_client: AsyncClient):
    """create → set_custom_field must not let a chained status rule fire (depth≤1).

    More precisely: create→set_status already covered in E26; here create→set_cf
    and a separate status_changed rule must not fire from the CF write (CF write
    does not emit status_changed). Also ensure create→set_cf + create→set_priority
    both can run at depth0 sequentially.
    """
    user = await _register(test_client, "e33_loop")
    h = _auth(user["token"], user["workspaceId"])
    await _create_cf(test_client, user, name="Src", key="src", type_="text")

    r1 = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "create→src",
            "triggerType": "issue.created",
            "actionType": "set_custom_field",
            "actionConfig": {"key": "src", "value": "bot"},
        },
    )
    assert r1.status_code == 200, r1.text

    r2 = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "create→high",
            "triggerType": "issue.created",
            "actionType": "set_priority",
            "actionConfig": {"priority": "high"},
        },
    )
    assert r2.status_code == 200, r2.text

    # A status_changed rule that would be dangerous if set_cf somehow changed status
    r3 = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "status→critical",
            "triggerType": "issue.status_changed",
            "actionType": "set_priority",
            "actionConfig": {"priority": "critical"},
        },
    )
    assert r3.status_code == 200, r3.text

    issue = await _create_issue(test_client, user, "loop-cf")
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    body = got.json()["data"]
    assert body["priority"] == "high"  # r2 ran; r3 did not
    assert body["status"] == "open"

    filtered = await test_client.get("/api/issues", headers=h, params={"cf.src": "bot"})
    rows = filtered.json()["data"]
    if isinstance(rows, dict):
        rows = rows.get("rows") or rows.get("items") or []
    assert any(r["id"] == issue["id"] for r in rows)


@pytest.mark.asyncio
async def test_condition_is_empty_and_neq(test_client: AsyncClient):
    user = await _register(test_client, "e33_empty")
    h = _auth(user["token"], user["workspaceId"])
    await _create_cf(test_client, user, name="OwnerCF", key="owner_cf", type_="text")
    issue = await _create_issue(test_client, user, "empty-cf")
    # no value set → is_empty matches

    rule = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "empty→comment",
            "triggerType": "issue.status_changed",
            "triggerConfig": {"to": "in_progress"},
            "condition": {"custom_field": {"key": "owner_cf", "op": "is_empty"}},
            "actionType": "add_comment",
            "actionConfig": {"content": "fill-owner"},
        },
    )
    assert rule.status_code == 200, rule.text

    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"status": "in_progress"},
    )
    comments = await test_client.get(f"/api/issues/{issue['id']}/comments", headers=h)
    rows = comments.json()["data"]
    if isinstance(rows, dict):
        rows = rows.get("rows") or rows.get("items") or []
    assert any("fill-owner" in (c.get("content") or "") for c in rows)

    # set value then neq should match
    await _set_cf(test_client, user, issue["id"], [{"key": "owner_cf", "value": "alice"}])
    r2 = await test_client.post(
        "/api/automations",
        headers=h,
        json={
            "name": "neq-bob→low",
            "triggerType": "issue.status_changed",
            "triggerConfig": {"to": "closed"},
            "condition": {
                "customField": {"key": "owner_cf", "op": "neq", "value": "bob"}
            },
            "actionType": "set_priority",
            "actionConfig": {"priority": "low"},
        },
    )
    assert r2.status_code == 200, r2.text
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"status": "closed"},
    )
    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.json()["data"]["priority"] == "low"
