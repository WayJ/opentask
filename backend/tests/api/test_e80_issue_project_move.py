"""E80: Issue project-move integrity — clear invalid milestone; duplicate edge."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e80"):
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


async def _project(client: AsyncClient, user: dict, name: str | None = None) -> dict:
    resp = await client.post(
        "/api/projects",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name or f"P-{uuid.uuid4().hex[:6]}", "description": "e80"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _milestone(
    client: AsyncClient, user: dict, project_id: str, name: str = "M1"
) -> dict:
    resp = await client.post(
        f"/api/projects/{project_id}/milestones",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _cycle(client: AsyncClient, user: dict, name: str = "C1") -> dict:
    start = datetime(2026, 11, 4, 0, 0, 0)
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


async def _issue(client: AsyncClient, user: dict, **extra) -> dict:
    body = {
        "title": extra.pop("title", "E80 issue"),
        "type": extra.pop("type", "bug"),
        "priority": extra.pop("priority", "medium"),
        "status": extra.pop("status", "open"),
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


def _timeline_entries(tl_payload):
    data = tl_payload if not isinstance(tl_payload, dict) else tl_payload
    if isinstance(data, dict):
        return data.get("rows") or data.get("items") or data.get("entries") or []
    return data or []


def _project_changed_data(entries):
    out = []
    for e in entries or []:
        at = str(e.get("actionType") or e.get("action_type") or "")
        if at == "project_changed":
            out.append(e.get("actionData") or e.get("action_data") or {})
    return out


@pytest.mark.asyncio
async def test_move_project_clears_milestone_keeps_cycle(test_client: AsyncClient):
    owner = await _register(test_client, "e80_move")
    h = _auth(owner["token"], owner["workspaceId"])
    p1 = await _project(test_client, owner, "A")
    p2 = await _project(test_client, owner, "B")
    ms = await _milestone(test_client, owner, p1["id"], "Ship-A")
    cy = await _cycle(test_client, owner)
    issue = await _issue(
        test_client,
        owner,
        project_id=p1["id"],
        milestone_id=ms["id"],
        cycle_id=cy["id"],
    )
    assert issue["milestone_id"] == ms["id"]
    assert issue["cycle_id"] == cy["id"]

    resp = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"project_id": p2["id"]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["project_id"] == p2["id"]
    assert data.get("milestone_id") in (None, "")
    assert data["cycle_id"] == cy["id"]

    got = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert got.json()["data"].get("milestone_id") in (None, "")
    assert got.json()["data"]["cycle_id"] == cy["id"]

    tl = await test_client.get(f"/api/issues/{issue['id']}/timeline", headers=h)
    assert tl.status_code == 200, tl.text
    pcs = _project_changed_data(_timeline_entries(tl.json()["data"]))
    assert pcs, "expected project_changed"
    assert pcs[-1].get("milestone_cleared") is True
    assert pcs[-1].get("milestone_from") == ms["id"]
    assert pcs[-1].get("from") == p1["id"]
    assert pcs[-1].get("to") == p2["id"]


@pytest.mark.asyncio
async def test_move_with_explicit_legal_milestone_keeps_it(test_client: AsyncClient):
    owner = await _register(test_client, "e80_keep")
    h = _auth(owner["token"], owner["workspaceId"])
    p1 = await _project(test_client, owner, "A")
    p2 = await _project(test_client, owner, "B")
    ms_a = await _milestone(test_client, owner, p1["id"], "A-ms")
    ms_b = await _milestone(test_client, owner, p2["id"], "B-ms")
    issue = await _issue(
        test_client, owner, project_id=p1["id"], milestone_id=ms_a["id"]
    )

    resp = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"project_id": p2["id"], "milestone_id": ms_b["id"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["milestone_id"] == ms_b["id"]
    assert resp.json()["data"]["project_id"] == p2["id"]


@pytest.mark.asyncio
async def test_move_with_illegal_milestone_returns_400(test_client: AsyncClient):
    owner = await _register(test_client, "e80_bad")
    h = _auth(owner["token"], owner["workspaceId"])
    p1 = await _project(test_client, owner, "A")
    p2 = await _project(test_client, owner, "B")
    ms_a = await _milestone(test_client, owner, p1["id"], "A-ms")
    issue = await _issue(
        test_client, owner, project_id=p1["id"], milestone_id=ms_a["id"]
    )

    resp = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"project_id": p2["id"], "milestone_id": ms_a["id"]},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_clear_project_clears_milestone(test_client: AsyncClient):
    owner = await _register(test_client, "e80_null")
    h = _auth(owner["token"], owner["workspaceId"])
    p1 = await _project(test_client, owner, "A")
    ms = await _milestone(test_client, owner, p1["id"])
    issue = await _issue(
        test_client, owner, project_id=p1["id"], milestone_id=ms["id"]
    )

    resp = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"project_id": None},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data.get("project_id") in (None, "")
    assert data.get("milestone_id") in (None, "")


@pytest.mark.asyncio
async def test_same_value_project_resubmit_keeps_milestone(test_client: AsyncClient):
    owner = await _register(test_client, "e80_same")
    h = _auth(owner["token"], owner["workspaceId"])
    p1 = await _project(test_client, owner, "A")
    ms = await _milestone(test_client, owner, p1["id"])
    issue = await _issue(
        test_client, owner, project_id=p1["id"], milestone_id=ms["id"]
    )

    resp = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"project_id": p1["id"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["milestone_id"] == ms["id"]


@pytest.mark.asyncio
async def test_duplicate_cross_project_does_not_copy_milestone(test_client: AsyncClient):
    owner = await _register(test_client, "e80_dup")
    h = _auth(owner["token"], owner["workspaceId"])
    p1 = await _project(test_client, owner, "A")
    p2 = await _project(test_client, owner, "B")
    ms = await _milestone(test_client, owner, p1["id"])
    src = await _issue(
        test_client, owner, project_id=p1["id"], milestone_id=ms["id"], title="src"
    )

    resp = await test_client.post(
        f"/api/issues/{src['id']}/duplicate",
        headers=h,
        json={"project_id": p2["id"]},
    )
    assert resp.status_code == 200, resp.text
    dup = resp.json()["data"]
    assert dup["project_id"] == p2["id"]
    assert dup.get("milestone_id") in (None, "")


@pytest.mark.asyncio
async def test_duplicate_same_project_still_copies_milestone(test_client: AsyncClient):
    owner = await _register(test_client, "e80_dup_same")
    h = _auth(owner["token"], owner["workspaceId"])
    p1 = await _project(test_client, owner, "A")
    ms = await _milestone(test_client, owner, p1["id"])
    src = await _issue(
        test_client, owner, project_id=p1["id"], milestone_id=ms["id"], title="src2"
    )

    resp = await test_client.post(
        f"/api/issues/{src['id']}/duplicate",
        headers=h,
        json={},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["milestone_id"] == ms["id"]
    assert resp.json()["data"]["project_id"] == p1["id"]


@pytest.mark.asyncio
async def test_viewer_cannot_move_project(test_client: AsyncClient):
    owner = await _register(test_client, "e80_own")
    viewer = await _register(test_client, "e80_view")
    await _add_member(test_client, owner, viewer, role="viewer")
    p1 = await _project(test_client, owner, "A")
    p2 = await _project(test_client, owner, "B")
    issue = await _issue(test_client, owner, project_id=p1["id"])

    resp = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(viewer["token"], owner["workspaceId"]),
        json={"project_id": p2["id"]},
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_project_move_no_new_webhook_event_name(test_client: AsyncClient):
    owner = await _register(test_client, "e80_wh")
    h = _auth(owner["token"], owner["workspaceId"])
    p1 = await _project(test_client, owner, "A")
    p2 = await _project(test_client, owner, "B")
    ms = await _milestone(test_client, owner, p1["id"])
    issue = await _issue(
        test_client, owner, project_id=p1["id"], milestone_id=ms["id"]
    )

    with patch(
        "opentask.services.issue_service.fire_webhooks", new_callable=AsyncMock
    ) as spy:
        resp = await test_client.put(
            f"/api/issues/{issue['id']}",
            headers=h,
            json={"project_id": p2["id"]},
        )
        assert resp.status_code == 200, resp.text
        event_types = [
            c.kwargs.get("event_type") or (c.args[1] if len(c.args) > 1 else None)
            for c in spy.await_args_list
        ]
        # flatten from kwargs
        event_types = []
        for c in spy.await_args_list:
            et = c.kwargs.get("event_type")
            if et:
                event_types.append(et)
        assert "issue.project_changed" in event_types
        assert not any(
            t and "milestone" in t and t != "issue.project_changed"
            for t in event_types
        )
        # no brand-new milestone_cleared webhook
        assert "issue.milestone_cleared" not in event_types
