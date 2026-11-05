"""E77: Issue trash/restore mid — list trash, restore, isolation, timeline."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select, text


async def _register(client: AsyncClient, prefix: str = "e77"):
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
        "title": extra.pop("title", "E77 issue"),
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


@pytest.mark.asyncio
async def test_trash_list_and_restore_roundtrip(test_client: AsyncClient):
    owner = await _register(test_client, "e77_rt")
    h = _auth(owner["token"], owner["workspaceId"])
    issue = await _issue(test_client, owner, title="to trash")

    # soft-delete
    d = await test_client.delete(f"/api/issues/{issue['id']}", headers=h)
    assert d.status_code == 200, d.text

    # default list / get hide deleted
    lst = await test_client.get("/api/issues", headers=h)
    assert lst.status_code == 200
    ids = [r["id"] for r in lst.json()["data"]["rows"]]
    assert issue["id"] not in ids

    g = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    assert g.status_code == 404

    # trash visible
    trash = await test_client.get("/api/issues/trash", headers=h)
    assert trash.status_code == 200, trash.text
    tdata = trash.json()["data"]
    assert tdata["total"] >= 1
    trow = next(r for r in tdata["rows"] if r["id"] == issue["id"])
    assert trow["title"] == "to trash"
    assert trow.get("isDeleted") is True or trow.get("is_deleted") is True

    # restore
    r = await test_client.post(f"/api/issues/{issue['id']}/restore", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["id"] == issue["id"]
    assert body.get("isDeleted") is False or body.get("is_deleted") is False

    # back in list; gone from trash
    lst2 = await test_client.get("/api/issues", headers=h)
    ids2 = [x["id"] for x in lst2.json()["data"]["rows"]]
    assert issue["id"] in ids2

    trash2 = await test_client.get("/api/issues/trash", headers=h)
    ids_t = [x["id"] for x in trash2.json()["data"]["rows"]]
    assert issue["id"] not in ids_t

    # timeline restored
    tl = await test_client.get(f"/api/issues/{issue['id']}/timeline", headers=h)
    assert tl.status_code == 200, tl.text
    tl_data = tl.json()["data"]
    entries = tl_data.get("rows") if isinstance(tl_data, dict) else tl_data
    actions = [
        str(e.get("actionType") or e.get("action_type") or "")
        for e in (entries or [])
    ]
    assert "restored" in actions


@pytest.mark.asyncio
async def test_restore_idempotent_and_viewer_forbidden(test_client: AsyncClient):
    owner = await _register(test_client, "e77_id")
    viewer = await _register(test_client, "e77_vw")
    await _add_member(test_client, owner, viewer, role="viewer")
    h = _auth(owner["token"], owner["workspaceId"])
    hv = _auth(viewer["token"], owner["workspaceId"])
    issue = await _issue(test_client, owner, title="live one")

    # live restore → 200 idempotent
    r0 = await test_client.post(f"/api/issues/{issue['id']}/restore", headers=h)
    assert r0.status_code == 200, r0.text

    await test_client.delete(f"/api/issues/{issue['id']}", headers=h)

    # viewer can list trash
    tv = await test_client.get("/api/issues/trash", headers=hv)
    assert tv.status_code == 200, tv.text
    assert any(r["id"] == issue["id"] for r in tv.json()["data"]["rows"])

    # viewer cannot restore
    rv = await test_client.post(f"/api/issues/{issue['id']}/restore", headers=hv)
    assert rv.status_code == 403, rv.text

    # member restore ok
    rm = await test_client.post(f"/api/issues/{issue['id']}/restore", headers=h)
    assert rm.status_code == 200, rm.text

    # second restore still 200
    r2 = await test_client.post(f"/api/issues/{issue['id']}/restore", headers=h)
    assert r2.status_code == 200, r2.text


@pytest.mark.asyncio
async def test_cross_ws_404_and_no_child_cascade(test_client: AsyncClient):
    owner = await _register(test_client, "e77_ws")
    other = await _register(test_client, "e77_ot")
    h = _auth(owner["token"], owner["workspaceId"])
    ho = _auth(other["token"], other["workspaceId"])

    parent = await _issue(test_client, owner, title="parent")
    child = await _issue(
        test_client, owner, title="child", parent_issue_id=parent["id"]
    )
    await test_client.delete(f"/api/issues/{child['id']}", headers=h)
    await test_client.delete(f"/api/issues/{parent['id']}", headers=h)

    # other WS restore → 404
    rx = await test_client.post(
        f"/api/issues/{parent['id']}/restore", headers=ho
    )
    assert rx.status_code == 404, rx.text

    # restore parent only — child stays deleted
    rp = await test_client.post(f"/api/issues/{parent['id']}/restore", headers=h)
    assert rp.status_code == 200, rp.text

    trash = await test_client.get("/api/issues/trash", headers=h)
    trash_ids = [r["id"] for r in trash.json()["data"]["rows"]]
    assert child["id"] in trash_ids
    assert parent["id"] not in trash_ids

    gc = await test_client.get(f"/api/issues/{child['id']}", headers=h)
    assert gc.status_code == 404


@pytest.mark.asyncio
async def test_include_deleted_get_and_no_new_webhook_name(test_client: AsyncClient):
    owner = await _register(test_client, "e77_wh")
    h = _auth(owner["token"], owner["workspaceId"])
    issue = await _issue(test_client, owner, title="hook check")
    await test_client.delete(f"/api/issues/{issue['id']}", headers=h)

    gd = await test_client.get(
        f"/api/issues/{issue['id']}",
        headers=h,
        params={"include_deleted": "true"},
    )
    assert gd.status_code == 200, gd.text
    data = gd.json()["data"]
    assert data["id"] == issue["id"]
    assert data.get("isDeleted") is True or data.get("is_deleted") is True

    with patch(
        "opentask.services.issue_service.publish_issue_created",
        new_callable=AsyncMock,
    ) as created_spy, patch(
        "opentask.services.workspace_webhook.service.WorkspaceWebhookService.dispatch",
        new_callable=AsyncMock,
        create=True,
    ):
        r = await test_client.post(f"/api/issues/{issue['id']}/restore", headers=h)
        assert r.status_code == 200, r.text
        # restore must NOT fire issue.created
        assert created_spy.await_count == 0
