"""E76: Issue external links mid — issue_links CRUD, caps, timeline, isolation."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select


async def _register(client: AsyncClient, prefix: str = "e76"):
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
        "title": extra.pop("title", "E76 issue"),
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
async def test_create_list_order_and_empty_title(test_client: AsyncClient):
    owner = await _register(test_client, "e76_ord")
    h = _auth(owner["token"], owner["workspaceId"])
    issue = await _issue(test_client, owner)

    r1 = await test_client.post(
        f"/api/issues/{issue['id']}/links",
        headers=h,
        json={"url": "https://figma.com/file/a", "title": "Design"},
    )
    assert r1.status_code == 200, r1.text
    link1 = r1.json()["data"]
    assert link1["url"] == "https://figma.com/file/a"
    assert link1["title"] == "Design"
    assert link1["position"] == 0

    r2 = await test_client.post(
        f"/api/issues/{issue['id']}/links",
        headers=h,
        json={"url": "https://notion.so/doc"},
    )
    assert r2.status_code == 200, r2.text
    link2 = r2.json()["data"]
    assert link2["title"] is None
    assert link2["position"] == 1

    listed = await test_client.get(f"/api/issues/{issue['id']}/links", headers=h)
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]["rows"]
    assert [x["id"] for x in rows] == [link1["id"], link2["id"]]
    assert [x["position"] for x in rows] == [0, 1]


@pytest.mark.asyncio
async def test_rejects_bad_url_and_cap_50(test_client: AsyncClient):
    owner = await _register(test_client, "e76_cap")
    h = _auth(owner["token"], owner["workspaceId"])
    issue = await _issue(test_client, owner)

    for bad in ["javascript:alert(1)", "/relative", "", "ftp://x.com"]:
        bad_r = await test_client.post(
            f"/api/issues/{issue['id']}/links",
            headers=h,
            json={"url": bad},
        )
        # empty → pydantic 422; others → service 400
        assert bad_r.status_code in (400, 422), (bad, bad_r.text)

    for i in range(50):
        ok = await test_client.post(
            f"/api/issues/{issue['id']}/links",
            headers=h,
            json={"url": f"https://example.com/{i}"},
        )
        assert ok.status_code == 200, ok.text

    over = await test_client.post(
        f"/api/issues/{issue['id']}/links",
        headers=h,
        json={"url": "https://example.com/51"},
    )
    assert over.status_code == 400, over.text


@pytest.mark.asyncio
async def test_cross_ws_404_viewer_read_ok_write_403(test_client: AsyncClient):
    owner = await _register(test_client, "e76_acl")
    viewer = await _register(test_client, "e76_vw")
    other = await _register(test_client, "e76_ot")
    await _add_member(test_client, owner, viewer, role="viewer")

    issue = await _issue(test_client, owner)
    h_owner = _auth(owner["token"], owner["workspaceId"])
    created = await test_client.post(
        f"/api/issues/{issue['id']}/links",
        headers=h_owner,
        json={"url": "https://docs.example.com/x"},
    )
    assert created.status_code == 200, created.text
    link_id = created.json()["data"]["id"]

    h_viewer = _auth(viewer["token"], owner["workspaceId"])
    get_r = await test_client.get(f"/api/issues/{issue['id']}/links", headers=h_viewer)
    assert get_r.status_code == 200, get_r.text

    post_r = await test_client.post(
        f"/api/issues/{issue['id']}/links",
        headers=h_viewer,
        json={"url": "https://evil.example.com"},
    )
    assert post_r.status_code == 403, post_r.text

    del_r = await test_client.delete(
        f"/api/issues/{issue['id']}/links/{link_id}",
        headers=h_viewer,
    )
    assert del_r.status_code == 403, del_r.text

    # other workspace → 404
    h_other = _auth(other["token"], other["workspaceId"])
    cross = await test_client.get(f"/api/issues/{issue['id']}/links", headers=h_other)
    assert cross.status_code == 404, cross.text


@pytest.mark.asyncio
async def test_patch_delete_and_timeline_add_remove_only(test_client: AsyncClient):
    owner = await _register(test_client, "e76_tl")
    h = _auth(owner["token"], owner["workspaceId"])
    issue = await _issue(test_client, owner)

    created = await test_client.post(
        f"/api/issues/{issue['id']}/links",
        headers=h,
        json={"url": "https://dash.example.com", "title": "Dash"},
    )
    assert created.status_code == 200, created.text
    link = created.json()["data"]

    # title-only patch → 200, no new timeline spam
    patched = await test_client.patch(
        f"/api/issues/{issue['id']}/links/{link['id']}",
        headers=h,
        json={"title": "Dashboard"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["title"] == "Dashboard"

    # position patch
    pos = await test_client.patch(
        f"/api/issues/{issue['id']}/links/{link['id']}",
        headers=h,
        json={"position": 3},
    )
    assert pos.status_code == 200, pos.text
    assert pos.json()["data"]["position"] == 3

    tl = await test_client.get(f"/api/issues/{issue['id']}/timeline", headers=h)
    assert tl.status_code == 200, tl.text
    tl_data = tl.json()["data"]
    entries = tl_data.get("rows") if isinstance(tl_data, dict) else tl_data
    actions = [
        str(t.get("action_type") or t.get("actionType") or "")
        for t in (entries or [])
    ]
    assert actions.count("link_added") == 1
    assert "link_removed" not in actions
    assert "link_updated" not in actions

    deleted = await test_client.delete(
        f"/api/issues/{issue['id']}/links/{link['id']}",
        headers=h,
    )
    assert deleted.status_code == 200, deleted.text

    tl2 = await test_client.get(f"/api/issues/{issue['id']}/timeline", headers=h)
    tl2_data = tl2.json()["data"]
    entries2 = tl2_data.get("rows") if isinstance(tl2_data, dict) else tl2_data
    actions2 = [
        str(t.get("action_type") or t.get("actionType") or "")
        for t in (entries2 or [])
    ]
    assert actions2.count("link_removed") == 1

    listed = await test_client.get(f"/api/issues/{issue['id']}/links", headers=h)
    assert listed.json()["data"]["rows"] == []


@pytest.mark.asyncio
async def test_does_not_touch_vcs_attachments_or_relations(test_client: AsyncClient, test_session):
    owner = await _register(test_client, "e76_iso")
    h = _auth(owner["token"], owner["workspaceId"])
    issue = await _issue(test_client, owner)

    created = await test_client.post(
        f"/api/issues/{issue['id']}/links",
        headers=h,
        json={"url": "https://example.com/iso"},
    )
    assert created.status_code == 200, created.text

    from opentask.models.issue_vcs_link import IssueVcsLink
    from opentask.models.issue.model import IssueRelation

    vcs = (
        await test_session.execute(
            select(IssueVcsLink).where(IssueVcsLink.issue_id == issue["id"])
        )
    ).scalars().all()
    assert vcs == []

    rels = (
        await test_session.execute(
            select(IssueRelation).where(IssueRelation.source_id == issue["id"])
        )
    ).scalars().all()
    assert rels == []
