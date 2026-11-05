"""E78: Issue set-parent / clear-parent mid — timeline parent_changed, reject deleted parent."""
from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e78"):
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
        "title": extra.pop("title", "E78 issue"),
        "type": extra.pop("type", "bug"),
        "priority": extra.pop("priority", "medium"),
        "description": extra.pop("description", "desc"),
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


def _timeline_actions(entries) -> list[str]:
    return [
        str(e.get("actionType") or e.get("action_type") or "")
        for e in (entries or [])
    ]


def _parent_changed_entries(entries):
    out = []
    for e in entries or []:
        at = str(e.get("actionType") or e.get("action_type") or "")
        if at == "parent_changed":
            out.append(e.get("actionData") or e.get("action_data") or {})
    return out


@pytest.mark.asyncio
async def test_set_parent_writes_timeline_parent_changed(test_client: AsyncClient):
    owner = await _register(test_client, "e78_set")
    h = _auth(owner["token"], owner["workspaceId"])
    parent = await _issue(test_client, owner, title="parent")
    child = await _issue(test_client, owner, title="child")

    resp = await test_client.put(
        f"/api/issues/{child['id']}",
        headers=h,
        json={"parent_issue_id": parent["id"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["parent_issue_id"] == parent["id"]

    tl = await test_client.get(f"/api/issues/{child['id']}/timeline", headers=h)
    assert tl.status_code == 200, tl.text
    tl_data = tl.json()["data"]
    entries = tl_data.get("rows") if isinstance(tl_data, dict) else tl_data
    assert "parent_changed" in _timeline_actions(entries)
    pcs = _parent_changed_entries(entries)
    assert pcs, "expected parent_changed action_data"
    assert pcs[-1].get("from") in (None, "")
    assert pcs[-1].get("to") == parent["id"]


@pytest.mark.asyncio
async def test_clear_parent_null_timeline_to_null(test_client: AsyncClient):
    owner = await _register(test_client, "e78_clr")
    h = _auth(owner["token"], owner["workspaceId"])
    parent = await _issue(test_client, owner, title="p")
    child = await _issue(
        test_client, owner, title="c", parent_issue_id=parent["id"]
    )

    resp = await test_client.put(
        f"/api/issues/{child['id']}",
        headers=h,
        json={"parent_issue_id": None},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["parent_issue_id"] is None

    tl = await test_client.get(f"/api/issues/{child['id']}/timeline", headers=h)
    entries = tl.json()["data"]
    if isinstance(entries, dict):
        entries = entries.get("rows")
    pcs = _parent_changed_entries(entries)
    assert pcs
    assert pcs[-1].get("from") == parent["id"]
    assert pcs[-1].get("to") is None


@pytest.mark.asyncio
async def test_omit_parent_field_no_change_and_same_value_skips_timeline(
    test_client: AsyncClient,
):
    owner = await _register(test_client, "e78_omit")
    h = _auth(owner["token"], owner["workspaceId"])
    parent = await _issue(test_client, owner, title="p")
    child = await _issue(
        test_client, owner, title="c", parent_issue_id=parent["id"]
    )

    # omit → parent unchanged
    resp = await test_client.put(
        f"/api/issues/{child['id']}",
        headers=h,
        json={"title": "c-renamed"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["parent_issue_id"] == parent["id"]

    tl0 = await test_client.get(f"/api/issues/{child['id']}/timeline", headers=h)
    entries0 = tl0.json()["data"]
    if isinstance(entries0, dict):
        entries0 = entries0.get("rows")
    count0 = len(_parent_changed_entries(entries0))

    # same parent again → no new parent_changed
    resp2 = await test_client.put(
        f"/api/issues/{child['id']}",
        headers=h,
        json={"parent_issue_id": parent["id"]},
    )
    assert resp2.status_code == 200, resp2.text
    tl1 = await test_client.get(f"/api/issues/{child['id']}/timeline", headers=h)
    entries1 = tl1.json()["data"]
    if isinstance(entries1, dict):
        entries1 = entries1.get("rows")
    assert len(_parent_changed_entries(entries1)) == count0


@pytest.mark.asyncio
async def test_reject_self_cycle_cross_ws_and_deleted_parent(
    test_client: AsyncClient,
):
    owner = await _register(test_client, "e78_rej")
    other = await _register(test_client, "e78_ot")
    h = _auth(owner["token"], owner["workspaceId"])
    a = await _issue(test_client, owner, title="a")
    b = await _issue(test_client, owner, title="b", parent_issue_id=a["id"])
    foreign = await _issue(test_client, other, title="foreign")

    # self
    r_self = await test_client.put(
        f"/api/issues/{a['id']}",
        headers=h,
        json={"parent_issue_id": a["id"]},
    )
    assert r_self.status_code == 400, r_self.text

    # cycle a→b
    r_cyc = await test_client.put(
        f"/api/issues/{a['id']}",
        headers=h,
        json={"parent_issue_id": b["id"]},
    )
    assert r_cyc.status_code == 400, r_cyc.text

    # cross WS
    r_x = await test_client.put(
        f"/api/issues/{a['id']}",
        headers=h,
        json={"parent_issue_id": foreign["id"]},
    )
    assert r_x.status_code == 400, r_x.text

    # soft-deleted parent (Q3a)
    dead = await _issue(test_client, owner, title="dead-parent")
    await test_client.delete(f"/api/issues/{dead['id']}", headers=h)
    r_del = await test_client.put(
        f"/api/issues/{a['id']}",
        headers=h,
        json={"parent_issue_id": dead["id"]},
    )
    assert r_del.status_code == 400, r_del.text
    detail = str(r_del.json().get("detail") or r_del.text)
    assert "删除" in detail or "deleted" in detail.lower() or "不存在" in detail


@pytest.mark.asyncio
async def test_viewer_parent_write_403_and_no_new_webhook_name(
    test_client: AsyncClient,
):
    owner = await _register(test_client, "e78_vw")
    viewer = await _register(test_client, "e78_v")
    await _add_member(test_client, owner, viewer, role="viewer")
    h = _auth(owner["token"], owner["workspaceId"])
    hv = _auth(viewer["token"], owner["workspaceId"])
    parent = await _issue(test_client, owner, title="p")
    child = await _issue(test_client, owner, title="c")

    denied = await test_client.put(
        f"/api/issues/{child['id']}",
        headers=hv,
        json={"parent_issue_id": parent["id"]},
    )
    assert denied.status_code == 403, denied.text

    with patch(
        "opentask.services.workspace_webhook.service.WorkspaceWebhookService.dispatch",
        new_callable=AsyncMock,
        create=True,
    ) as dispatch_spy:
        ok = await test_client.put(
            f"/api/issues/{child['id']}",
            headers=h,
            json={"parent_issue_id": parent["id"]},
        )
        assert ok.status_code == 200, ok.text
        for call in dispatch_spy.await_args_list:
            args = call.args + tuple(call.kwargs.values())
            flat = " ".join(str(a) for a in args)
            assert "parent_changed" not in flat
            assert "issue.parent_changed" not in flat


@pytest.mark.asyncio
async def test_child_progress_module_untouched():
    """E78 must not rewrite E70 childProgress computation."""
    path = (
        Path(__file__).resolve().parents[2]
        / "opentask"
        / "services"
        / "child_progress.py"
    )
    text = path.read_text(encoding="utf-8")
    assert "compute_child_progress" in text
    assert "CHILD_PROGRESS_DONE_STATUSES" in text
    # marker that E78 didn't add parent-change logic into this file
    assert "parent_changed" not in text
    assert "E78" not in text
