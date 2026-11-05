"""E65: Initiative relations mid (blocks / is_blocked_by / relates_to)."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from opentask.models.initiative.model import INITIATIVE_RELATION_TYPES, InitiativeRelation


def test_e65_relation_types_q1a():
    assert INITIATIVE_RELATION_TYPES == ("blocks", "is_blocked_by", "relates_to")
    assert InitiativeRelation.__tablename__ == "initiative_relations"


async def _register(client: AsyncClient, prefix: str = "e65"):
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
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


async def _ini(client: AsyncClient, h: dict, name: str) -> dict:
    r = await client.post("/api/initiatives", headers=h, json={"name": name})
    assert r.status_code == 200, r.text
    return r.json()["data"]


@pytest.mark.asyncio
async def test_e65_add_blocks_list_both_ends(test_client: AsyncClient):
    user = await _register(test_client, "e65_b")
    h = _auth(user["token"], user["workspaceId"])
    a = await _ini(test_client, h, "IniA")
    b = await _ini(test_client, h, "IniB")
    post = await test_client.post(
        f"/api/initiatives/{a['id']}/relations",
        headers=h,
        json={"targetInitiativeId": b["id"], "type": "blocks"},
    )
    assert post.status_code == 200, post.text
    item = post.json()["data"]
    assert item["type"] == "blocks"
    assert item["direction"] == "outgoing"
    assert item["initiative"]["id"] == b["id"]
    assert item["initiative"]["name"] == "IniB"

    la = await test_client.get(f"/api/initiatives/{a['id']}/relations", headers=h)
    assert la.status_code == 200, la.text
    items_a = la.json()["data"]["items"]
    assert any(
        i["initiative"]["id"] == b["id"]
        and i["type"] == "blocks"
        and i["direction"] == "outgoing"
        for i in items_a
    )

    lb = await test_client.get(f"/api/initiatives/{b['id']}/relations", headers=h)
    assert lb.status_code == 200, lb.text
    items_b = lb.json()["data"]["items"]
    assert any(
        i["initiative"]["id"] == a["id"]
        and i["type"] == "blocks"
        and i["direction"] == "incoming"
        for i in items_b
    )


@pytest.mark.asyncio
async def test_e65_self_loop_400(test_client: AsyncClient):
    user = await _register(test_client, "e65_sl")
    h = _auth(user["token"], user["workspaceId"])
    a = await _ini(test_client, h, "Self")
    r = await test_client.post(
        f"/api/initiatives/{a['id']}/relations",
        headers=h,
        json={"targetInitiativeId": a["id"], "type": "relates_to"},
    )
    assert r.status_code == 400, r.text


@pytest.mark.asyncio
async def test_e65_cross_ws_target_404(test_client: AsyncClient):
    u1 = await _register(test_client, "e65_c1")
    u2 = await _register(test_client, "e65_c2")
    h1 = _auth(u1["token"], u1["workspaceId"])
    h2 = _auth(u2["token"], u2["workspaceId"])
    a = await _ini(test_client, h1, "A")
    b = await _ini(test_client, h2, "B")
    r = await test_client.post(
        f"/api/initiatives/{a['id']}/relations",
        headers=h1,
        json={"targetInitiativeId": b["id"], "type": "blocks"},
    )
    assert r.status_code == 404, r.text


@pytest.mark.asyncio
async def test_e65_blocks_cycle_400(test_client: AsyncClient):
    user = await _register(test_client, "e65_cy")
    h = _auth(user["token"], user["workspaceId"])
    a = await _ini(test_client, h, "CA")
    b = await _ini(test_client, h, "CB")
    r1 = await test_client.post(
        f"/api/initiatives/{a['id']}/relations",
        headers=h,
        json={"targetInitiativeId": b["id"], "type": "blocks"},
    )
    assert r1.status_code == 200, r1.text
    r2 = await test_client.post(
        f"/api/initiatives/{b['id']}/relations",
        headers=h,
        json={"targetInitiativeId": a["id"], "type": "blocks"},
    )
    assert r2.status_code == 400, r2.text


@pytest.mark.asyncio
async def test_e65_relates_to_no_cycle_check(test_client: AsyncClient):
    user = await _register(test_client, "e65_rt")
    h = _auth(user["token"], user["workspaceId"])
    a = await _ini(test_client, h, "RA")
    b = await _ini(test_client, h, "RB")
    r1 = await test_client.post(
        f"/api/initiatives/{a['id']}/relations",
        headers=h,
        json={"targetInitiativeId": b["id"], "type": "relates_to"},
    )
    assert r1.status_code == 200, r1.text
    r2 = await test_client.post(
        f"/api/initiatives/{b['id']}/relations",
        headers=h,
        json={"targetInitiativeId": a["id"], "type": "relates_to"},
    )
    assert r2.status_code == 200, r2.text


@pytest.mark.asyncio
async def test_e65_is_blocked_by_literal_store_and_cycle(test_client: AsyncClient):
    user = await _register(test_client, "e65_ibb")
    h = _auth(user["token"], user["workspaceId"])
    a = await _ini(test_client, h, "IA")
    b = await _ini(test_client, h, "IB")
    post = await test_client.post(
        f"/api/initiatives/{a['id']}/relations",
        headers=h,
        json={"targetInitiativeId": b["id"], "type": "is_blocked_by"},
    )
    assert post.status_code == 200, post.text
    assert post.json()["data"]["type"] == "is_blocked_by"
    # A is_blocked_by B ≡ B blocks A. Adding A blocks B closes the cycle.
    r = await test_client.post(
        f"/api/initiatives/{a['id']}/relations",
        headers=h,
        json={"targetInitiativeId": b["id"], "type": "blocks"},
    )
    assert r.status_code == 400, r.text


@pytest.mark.asyncio
async def test_e65_viewer_write_403_delete_ok(test_client: AsyncClient):
    owner = await _register(test_client, "e65_ow")
    viewer = await _register(test_client, "e65_vw")
    await test_client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": viewer["userId"], "role": "viewer"},
    )
    oh = _auth(owner["token"], owner["workspaceId"])
    vh = _auth(viewer["token"], owner["workspaceId"])
    a = await _ini(test_client, oh, "VA")
    b = await _ini(test_client, oh, "VB")
    post = await test_client.post(
        f"/api/initiatives/{a['id']}/relations",
        headers=oh,
        json={"targetInitiativeId": b["id"], "type": "relates_to"},
    )
    assert post.status_code == 200, post.text
    rid = post.json()["data"]["id"]
    assert (
        await test_client.get(f"/api/initiatives/{a['id']}/relations", headers=vh)
    ).status_code == 200
    assert (
        await test_client.post(
            f"/api/initiatives/{a['id']}/relations",
            headers=vh,
            json={"targetInitiativeId": b["id"], "type": "blocks"},
        )
    ).status_code == 403
    assert (
        await test_client.delete(
            f"/api/initiatives/{a['id']}/relations/{rid}", headers=vh
        )
    ).status_code == 403
    deleted = await test_client.delete(
        f"/api/initiatives/{a['id']}/relations/{rid}", headers=oh
    )
    assert deleted.status_code == 200, deleted.text


@pytest.mark.asyncio
async def test_e65_detail_counts_default_list_opt_in(test_client: AsyncClient):
    user = await _register(test_client, "e65_ct")
    h = _auth(user["token"], user["workspaceId"])
    a = await _ini(test_client, h, "CntA")
    b = await _ini(test_client, h, "CntB")
    await test_client.post(
        f"/api/initiatives/{a['id']}/relations",
        headers=h,
        json={"targetInitiativeId": b["id"], "type": "blocks"},
    )
    detail = await test_client.get(f"/api/initiatives/{a['id']}", headers=h)
    d = detail.json()["data"]
    assert d["blocksCount"] == 1
    assert d["blockedByCount"] == 0
    detail_b = (await test_client.get(f"/api/initiatives/{b['id']}", headers=h)).json()[
        "data"
    ]
    assert detail_b["blocksCount"] == 0
    assert detail_b["blockedByCount"] == 1

    listed = await test_client.get("/api/initiatives", headers=h)
    row_a = next(r for r in listed.json()["data"]["rows"] if r["id"] == a["id"])
    assert "blocksCount" not in row_a

    listed2 = await test_client.get("/api/initiatives?include=relationCounts", headers=h)
    row_a2 = next(r for r in listed2.json()["data"]["rows"] if r["id"] == a["id"])
    assert row_a2["blocksCount"] == 1
    assert row_a2["blockedByCount"] == 0


@pytest.mark.asyncio
async def test_e65_relation_mutate_no_webhook_fire(test_client: AsyncClient):
    user = await _register(test_client, "e65_spy")
    h = _auth(user["token"], user["workspaceId"])
    a = await _ini(test_client, h, "SA")
    b = await _ini(test_client, h, "SB")
    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new_callable=AsyncMock,
    ) as fw:
        post = await test_client.post(
            f"/api/initiatives/{a['id']}/relations",
            headers=h,
            json={"targetInitiativeId": b["id"], "type": "relates_to"},
        )
        assert post.status_code == 200, post.text
        rid = post.json()["data"]["id"]
        deleted = await test_client.delete(
            f"/api/initiatives/{a['id']}/relations/{rid}", headers=h
        )
        assert deleted.status_code == 200, deleted.text
        fw.assert_not_called()
