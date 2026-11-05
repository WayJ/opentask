"""E75: Issue duplicate mid — whitelist copy, relates_to, CLI-facing API."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e75"):
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


async def _add_member(
    client: AsyncClient, owner: dict, member: dict, role: str = "member"
):
    resp = await client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": role},
    )
    assert resp.status_code == 200, resp.text


async def _issue(client: AsyncClient, user: dict, **extra) -> dict:
    body = {
        "title": extra.pop("title", "E75 source"),
        "type": extra.pop("type", "bug"),
        "priority": extra.pop("priority", "high"),
        "description": extra.pop("description", "desc body"),
        "status": extra.pop("status", "in_progress"),
        "reporter_id": user["userId"],
        **extra,
    }
    r = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]


@pytest.mark.asyncio
async def test_duplicate_copies_whitelist_and_resets_status(test_client: AsyncClient):
    owner = await _register(test_client, "e75_ok")
    a = await _register(test_client, "e75_asg")
    await _add_member(test_client, owner, a)
    h = _auth(owner["token"], owner["workspaceId"])

    parent = await _issue(test_client, owner, title="parent")
    src = await _issue(
        test_client,
        owner,
        title="Login bug",
        description="fix credentials",
        type="bug",
        priority="critical",
        status="in_progress",
        parent_issue_id=parent["id"],
        estimate_points=3,
        estimated_hours=4.5,
        assignee_ids=[a["userId"], owner["userId"]],
    )

    # tag
    tag = (
        await test_client.post(
            "/api/tags", headers=h, json={"name": f"t-{uuid.uuid4().hex[:6]}"}
        )
    ).json()["data"]
    await test_client.post(f"/api/issues/{src['id']}/tags/{tag['id']}", headers=h)

    # non-formula CF
    cf = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={"name": "Severity", "key": f"sev_{uuid.uuid4().hex[:6]}", "type": "text"},
        )
    ).json()["data"]
    await test_client.patch(
        f"/api/issues/{src['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": cf["id"], "value": "P0"}]},
    )

    # comments + child (must NOT copy)
    await test_client.post(
        f"/api/issues/{src['id']}/comments",
        headers=h,
        json={"content": "leave me"},
    )
    await test_client.post(
        f"/api/issues/{src['id']}/comments",
        headers=h,
        json={"content": "and me"},
    )
    await _issue(test_client, owner, title="child", parent_issue_id=src["id"])

    # existing relation on source should not copy
    other = await _issue(test_client, owner, title="related-other")
    await test_client.post(
        f"/api/issues/{src['id']}/relations",
        headers=h,
        params={"target_id": other["id"], "relation_type": "blocks"},
    )

    with patch(
        "opentask.services.issue_service.fire_webhooks",
        new_callable=AsyncMock,
    ) as wh:
        resp = await test_client.post(
            f"/api/issues/{src['id']}/duplicate",
            headers=h,
            json={},
        )
        assert resp.status_code == 200, resp.text
        types = [c.kwargs.get("event_type") for c in wh.await_args_list]
        assert "issue.created" in types
        assert "issue.duplicated" not in types

    dup = resp.json()["data"]
    assert dup["id"] != src["id"]
    assert dup["issue_code"] != src["issue_code"]
    assert dup["title"] == "Login bug (copy)"
    assert dup["description"] == "fix credentials"
    assert dup["type"] in ("bug", "BUG") or str(dup["type"]).endswith("bug")
    assert dup["status"] in ("open", "OPEN") or str(dup["status"]).lower() == "open"
    assert str(dup["priority"]).lower() == "critical"
    assert dup["parent_issue_id"] == parent["id"]
    assert dup.get("estimate_points") == 3 or float(dup.get("estimate_points") or 0) == 3.0
    assert dup["reporter_id"] == owner["userId"]
    assert (dup.get("comment_count") or 0) == 0
    assert (dup.get("attachment_count") or 0) == 0

    # assignees copied
    ids = [u["id"] for u in dup.get("assignees") or []]
    assert a["userId"] in ids
    assert owner["userId"] in ids

    # tags
    tags = (
        await test_client.get(f"/api/issues/{dup['id']}/tags", headers=h)
    ).json()["data"]
    tag_rows = tags.get("rows") if isinstance(tags, dict) else tags
    tag_ids = [t["id"] for t in (tag_rows or [])]
    assert tag["id"] in tag_ids

    # CF non-formula copied
    detail = await test_client.get(
        f"/api/issues/{dup['id']}",
        headers=h,
        params={"include": "customFields"},
    )
    assert detail.status_code == 200, detail.text
    cfs = detail.json()["data"].get("customFields") or []
    by_id = {c["fieldId"]: c for c in cfs}
    assert by_id[cf["id"]]["value"] == "P0"

    # no comments / no children
    comments = (
        await test_client.get(f"/api/issues/{dup['id']}/comments", headers=h)
    ).json()["data"]
    rows = comments.get("rows") if isinstance(comments, dict) else comments
    assert rows == [] or len(rows) == 0
    children = (
        await test_client.get(f"/api/issues/{dup['id']}/children", headers=h)
    ).json()["data"]
    child_rows = children if isinstance(children, list) else children.get("rows") or []
    assert child_rows == [] or len(child_rows) == 0

    # relations: only relates_to → source (Q4a); no blocks copy; no duplicates
    rel = (
        await test_client.get(f"/api/issues/{dup['id']}/relations", headers=h)
    ).json()["data"]
    as_source = rel.get("as_source") or []
    assert any(
        r.get("target_id") == src["id"]
        and str(r.get("relation_type")).lower().endswith("relates_to")
        for r in as_source
    )
    assert not any(
        str(r.get("relation_type")).lower().endswith("duplicates") for r in as_source
    )
    assert not any(
        r.get("target_id") == other["id"] for r in as_source
    )

    # timeline created has duplicated_from
    tl = (
        await test_client.get(f"/api/issues/{dup['id']}/timeline", headers=h)
    ).json()["data"]
    entries = tl.get("rows") if isinstance(tl, dict) else tl
    if isinstance(tl, dict) and "items" in tl:
        entries = tl["items"]
    created = [
        e
        for e in (entries or [])
        if str(e.get("action_type") or e.get("actionType") or "").lower().endswith(
            "created"
        )
        or str(e.get("action_type") or "") == "created"
    ]
    assert created, tl
    action_data = created[0].get("action_data") or created[0].get("actionData") or {}
    assert action_data.get("duplicated_from") in (src["id"], str(src["id"]))


@pytest.mark.asyncio
async def test_duplicate_skips_formula_cf(test_client: AsyncClient):
    owner = await _register(test_client, "e75_f")
    h = _auth(owner["token"], owner["workspaceId"])
    src = await _issue(test_client, owner, title="with-formula")

    weight = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={
                "name": "Weight",
                "key": f"w_{uuid.uuid4().hex[:6]}",
                "type": "number",
            },
        )
    ).json()["data"]
    await test_client.patch(
        f"/api/issues/{src['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": weight["id"], "value": 5}]},
    )
    formula = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={
                "name": "Double",
                "key": f"d_{uuid.uuid4().hex[:6]}",
                "type": "formula",
                "formulaExpr": f"COALESCE(cf.{weight['key']}, 0) * 2",
                "formulaResultType": "number",
            },
        )
    ).json()["data"]

    resp = await test_client.post(
        f"/api/issues/{src['id']}/duplicate", headers=h, json={}
    )
    assert resp.status_code == 200, resp.text
    dup = resp.json()["data"]

    detail = await test_client.get(
        f"/api/issues/{dup['id']}",
        headers=h,
        params={"include": "customFields"},
    )
    cfs = detail.json()["data"].get("customFields") or []
    by_id = {c["fieldId"]: c for c in cfs}
    assert by_id[weight["id"]]["value"] == 5
    # formula is computed, not stored — ensure we did not try to upsert it
    # (value may appear as computed; must not have a stored row from copy path)
    # soft assert: type formula entries are computed=True if present
    if formula["id"] in by_id:
        assert by_id[formula["id"]].get("computed") is True


@pytest.mark.asyncio
async def test_duplicate_overrides(test_client: AsyncClient):
    owner = await _register(test_client, "e75_ov")
    a = await _register(test_client, "e75_ova")
    await _add_member(test_client, owner, a)
    h = _auth(owner["token"], owner["workspaceId"])
    parent = await _issue(test_client, owner, title="p")
    src = await _issue(
        test_client,
        owner,
        title="Src",
        parent_issue_id=parent["id"],
        assignee_ids=[owner["userId"]],
    )
    resp = await test_client.post(
        f"/api/issues/{src['id']}/duplicate",
        headers=h,
        json={
            "title": "Overridden",
            "parent_issue_id": None,
            "assignee_ids": [a["userId"]],
        },
    )
    assert resp.status_code == 200, resp.text
    dup = resp.json()["data"]
    assert dup["title"] == "Overridden"
    assert dup.get("parent_issue_id") in (None, "")
    ids = [u["id"] for u in dup.get("assignees") or []]
    assert ids == [a["userId"]]


@pytest.mark.asyncio
async def test_duplicate_cross_ws_404_and_viewer_403(test_client: AsyncClient):
    owner = await _register(test_client, "e75_x")
    other = await _register(test_client, "e75_y")
    viewer = await _register(test_client, "e75_v")
    await _add_member(test_client, owner, viewer, role="viewer")
    h = _auth(owner["token"], owner["workspaceId"])
    src = await _issue(test_client, owner, title="priv")

    cross = await test_client.post(
        f"/api/issues/{src['id']}/duplicate",
        headers=_auth(other["token"], other["workspaceId"]),
        json={},
    )
    assert cross.status_code == 404, cross.text

    denied = await test_client.post(
        f"/api/issues/{src['id']}/duplicate",
        headers=_auth(viewer["token"], owner["workspaceId"]),
        json={},
    )
    assert denied.status_code == 403, denied.text
