"""E61: Insights shared reports (visibility personal|workspace) + fork · no-emit."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e61"):
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
    return resp.json()["data"]


async def _create_tag(client: AsyncClient, user: dict, name: str) -> dict:
    resp = await client.post(
        "/api/tags",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name, "color": "#22c55e"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# ---------------------------------------------------------------------------
# B · share / list / ACL
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_default_create_is_personal_and_invisible_to_peer(test_client: AsyncClient):
    owner = await _register(test_client, "e61_def")
    mate = await _register(test_client, "e61_defm")
    await _add_member(test_client, owner, mate, role="member")
    ho = _auth(owner["token"], owner["workspaceId"])
    hm = _auth(mate["token"], owner["workspaceId"])

    created = await test_client.post(
        "/api/insights/reports",
        headers=ho,
        json={"name": "Mine only", "filters": {}},
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["visibility"] == "personal"
    assert row["canEdit"] is True
    assert row["ownerUserId"] == str(owner["userId"])

    listed_mate = await test_client.get("/api/insights/reports", headers=hm)
    assert listed_mate.status_code == 200, listed_mate.text
    assert all(r["id"] != row["id"] for r in listed_mate.json()["data"]["rows"])


@pytest.mark.asyncio
async def test_share_visible_to_teammate_and_unshare(test_client: AsyncClient):
    owner = await _register(test_client, "e61_sh")
    mate = await _register(test_client, "e61_shm")
    await _add_member(test_client, owner, mate, role="member")
    ho = _auth(owner["token"], owner["workspaceId"])
    hm = _auth(mate["token"], owner["workspaceId"])

    created = await test_client.post(
        "/api/insights/reports",
        headers=ho,
        json={"name": "Team slice", "filters": {"labelIds": []}, "visibility": "personal"},
    )
    rid = created.json()["data"]["id"]

    shared = await test_client.patch(
        f"/api/insights/reports/{rid}",
        headers=ho,
        json={"visibility": "workspace"},
    )
    assert shared.status_code == 200, shared.text
    assert shared.json()["data"]["visibility"] == "workspace"
    assert shared.json()["data"]["canEdit"] is True

    listed_mate = await test_client.get("/api/insights/reports", headers=hm)
    assert listed_mate.status_code == 200, listed_mate.text
    rows = listed_mate.json()["data"]["rows"]
    hit = next(r for r in rows if r["id"] == rid)
    assert hit["visibility"] == "workspace"
    assert hit["canEdit"] is False
    assert hit["ownerUserId"] == str(owner["userId"])

    # unshare
    un = await test_client.patch(
        f"/api/insights/reports/{rid}",
        headers=ho,
        json={"visibility": "personal"},
    )
    assert un.status_code == 200, un.text
    listed2 = await test_client.get("/api/insights/reports", headers=hm)
    assert all(r["id"] != rid for r in listed2.json()["data"]["rows"])


@pytest.mark.asyncio
async def test_create_workspace_visibility_member_ok(test_client: AsyncClient):
    owner = await _register(test_client, "e61_cw")
    mate = await _register(test_client, "e61_cwm")
    await _add_member(test_client, owner, mate, role="member")
    hm = _auth(mate["token"], owner["workspaceId"])
    created = await test_client.post(
        "/api/insights/reports",
        headers=hm,
        json={"name": "Shared now", "filters": {}, "visibility": "workspace"},
    )
    assert created.status_code == 200, created.text
    assert created.json()["data"]["visibility"] == "workspace"


@pytest.mark.asyncio
async def test_non_owner_patch_delete_404(test_client: AsyncClient):
    owner = await _register(test_client, "e61_no")
    mate = await _register(test_client, "e61_nom")
    await _add_member(test_client, owner, mate, role="member")
    ho = _auth(owner["token"], owner["workspaceId"])
    hm = _auth(mate["token"], owner["workspaceId"])

    created = await test_client.post(
        "/api/insights/reports",
        headers=ho,
        json={"name": "Owned", "filters": {}, "visibility": "workspace"},
    )
    rid = created.json()["data"]["id"]

    bad_patch = await test_client.patch(
        f"/api/insights/reports/{rid}",
        headers=hm,
        json={"name": "hack"},
    )
    assert bad_patch.status_code == 404, bad_patch.text

    bad_vis = await test_client.patch(
        f"/api/insights/reports/{rid}",
        headers=hm,
        json={"visibility": "personal"},
    )
    assert bad_vis.status_code == 404, bad_vis.text

    bad_del = await test_client.delete(f"/api/insights/reports/{rid}", headers=hm)
    assert bad_del.status_code == 404, bad_del.text


@pytest.mark.asyncio
async def test_viewer_cannot_share_403(test_client: AsyncClient):
    owner = await _register(test_client, "e61_vw")
    viewer = await _register(test_client, "e61_vwv")
    await _add_member(test_client, owner, viewer, role="viewer")
    hv = _auth(viewer["token"], owner["workspaceId"])

    personal = await test_client.post(
        "/api/insights/reports",
        headers=hv,
        json={"name": "Viewer personal", "filters": {}},
    )
    assert personal.status_code == 200, personal.text
    rid = personal.json()["data"]["id"]

    create_ws = await test_client.post(
        "/api/insights/reports",
        headers=hv,
        json={"name": "Viewer share", "filters": {}, "visibility": "workspace"},
    )
    assert create_ws.status_code == 403, create_ws.text

    patch_ws = await test_client.patch(
        f"/api/insights/reports/{rid}",
        headers=hv,
        json={"visibility": "workspace"},
    )
    assert patch_ws.status_code == 403, patch_ws.text


@pytest.mark.asyncio
async def test_fork_copies_filters_as_personal(test_client: AsyncClient):
    owner = await _register(test_client, "e61_fk")
    mate = await _register(test_client, "e61_fkm")
    await _add_member(test_client, owner, mate, role="member")
    ho = _auth(owner["token"], owner["workspaceId"])
    hm = _auth(mate["token"], owner["workspaceId"])
    tag = await _create_tag(test_client, owner, "fork-tag")

    created = await test_client.post(
        "/api/insights/reports",
        headers=ho,
        json={
            "name": "Source",
            "filters": {"labelIds": [tag["id"]], "assigneeLimit": 7},
            "visibility": "workspace",
            "isDefault": True,
        },
    )
    rid = created.json()["data"]["id"]

    forked = await test_client.post(
        f"/api/insights/reports/{rid}/fork",
        headers=hm,
        json={},
    )
    assert forked.status_code == 200, forked.text
    copy = forked.json()["data"]
    assert copy["id"] != rid
    assert copy["ownerUserId"] == str(mate["userId"])
    assert copy["visibility"] == "personal"
    assert copy["isDefault"] is False
    assert copy["canEdit"] is True
    assert copy["filters"]["labelIds"] == [tag["id"]]
    assert copy["filters"]["assigneeLimit"] == 7
    assert copy["name"].startswith("副本")

    named = await test_client.post(
        f"/api/insights/reports/{rid}/fork",
        headers=hm,
        json={"name": "My copy"},
    )
    assert named.status_code == 200, named.text
    assert named.json()["data"]["name"] == "My copy"


@pytest.mark.asyncio
async def test_personal_cap_20_and_shared_cap_50(test_client: AsyncClient):
    owner = await _register(test_client, "e61_cap")
    ho = _auth(owner["token"], owner["workspaceId"])

    for i in range(20):
        resp = await test_client.post(
            "/api/insights/reports",
            headers=ho,
            json={"name": f"p{i}", "filters": {}, "visibility": "personal"},
        )
        assert resp.status_code == 200, resp.text
    over_p = await test_client.post(
        "/api/insights/reports",
        headers=ho,
        json={"name": "p-overflow", "filters": {}, "visibility": "personal"},
    )
    assert over_p.status_code == 400, over_p.text

    # shared creates do not consume personal slots for a fresh user
    other = await _register(test_client, "e61_caps")
    await _add_member(test_client, owner, other, role="member")
    hs = _auth(other["token"], owner["workspaceId"])
    for i in range(50):
        resp = await test_client.post(
            "/api/insights/reports",
            headers=hs,
            json={"name": f"s{i}", "filters": {}, "visibility": "workspace"},
        )
        assert resp.status_code == 200, resp.text
    over_s = await test_client.post(
        "/api/insights/reports",
        headers=hs,
        json={"name": "s-overflow", "filters": {}, "visibility": "workspace"},
    )
    assert over_s.status_code == 400, over_s.text


@pytest.mark.asyncio
async def test_cross_tenant_cannot_see_shared(test_client: AsyncClient):
    a = await _register(test_client, "e61_xa")
    b = await _register(test_client, "e61_xb")
    ha = _auth(a["token"], a["workspaceId"])
    hb = _auth(b["token"], b["workspaceId"])

    created = await test_client.post(
        "/api/insights/reports",
        headers=ha,
        json={"name": "A shared", "filters": {}, "visibility": "workspace"},
    )
    rid = created.json()["data"]["id"]

    listed_b = await test_client.get("/api/insights/reports", headers=hb)
    assert all(r["id"] != rid for r in listed_b.json()["data"]["rows"])

    fork_b = await test_client.post(
        f"/api/insights/reports/{rid}/fork",
        headers=hb,
        json={},
    )
    assert fork_b.status_code == 404, fork_b.text


@pytest.mark.asyncio
async def test_share_keeps_default_and_no_inbox_broadcast(test_client: AsyncClient):
    owner = await _register(test_client, "e61_dg")
    mate = await _register(test_client, "e61_dgm")
    await _add_member(test_client, owner, mate, role="member")
    ho = _auth(owner["token"], owner["workspaceId"])
    hm = _auth(mate["token"], owner["workspaceId"])

    created = await test_client.post(
        "/api/insights/reports",
        headers=ho,
        json={"name": "Default shared", "filters": {}, "isDefault": True},
    )
    rid = created.json()["data"]["id"]
    assert created.json()["data"]["isDefault"] is True

    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new_callable=AsyncMock,
    ) as fire_spy:
        shared = await test_client.patch(
            f"/api/insights/reports/{rid}",
            headers=ho,
            json={"visibility": "workspace"},
        )
        assert shared.status_code == 200, shared.text
        assert shared.json()["data"]["isDefault"] is True
        assert shared.json()["data"]["visibility"] == "workspace"
        fire_spy.assert_not_called()

    inbox_mate = await test_client.get("/api/inbox", headers=hm)
    assert inbox_mate.status_code == 200, inbox_mate.text
    rows = inbox_mate.json()["data"]["rows"]
    assert not any("report" in str(r.get("type", "")).lower() for r in rows)
    assert not any("share" in str(r.get("title", "")).lower() for r in rows)


@pytest.mark.asyncio
async def test_digest_uses_own_default_not_peer_shared(test_client: AsyncClient):
    owner = await _register(test_client, "e61_dd")
    mate = await _register(test_client, "e61_ddm")
    await _add_member(test_client, owner, mate, role="member")
    ho = _auth(owner["token"], owner["workspaceId"])
    hm = _auth(mate["token"], owner["workspaceId"])

    await test_client.put(
        "/api/inbox/preferences",
        headers=hm,
        json={"insights_digest": True},
    )
    # peer shares a default report — must NOT become mate's digest source auto
    await test_client.post(
        "/api/insights/reports",
        headers=ho,
        json={
            "name": "Owner default shared",
            "filters": {},
            "isDefault": True,
            "visibility": "workspace",
        },
    )

    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new_callable=AsyncMock,
    ) as fire_spy:
        tick = await test_client.post("/api/insights/run-digest", headers=ho)
        assert tick.status_code == 200, tick.text
        # mate enabled; owner tick as writer should deliver to mate with WS fallback
        assert tick.json()["data"]["created"] >= 1
        fire_spy.assert_not_called()

    inbox = await test_client.get("/api/inbox", headers=hm)
    digests = [r for r in inbox.json()["data"]["rows"] if r["type"] == "insights_digest"]
    assert len(digests) == 1
