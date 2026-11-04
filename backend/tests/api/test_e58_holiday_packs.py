"""E58: holiday packs list/show/preview/apply + no-emit."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(test_client: AsyncClient, prefix: str = "e58", *, username: str | None = None):
    uname = username or f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    resp = await test_client.post(
        "/api/auth/register",
        json={"userName": uname, "password": password, "name": uname},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    return {
        "username": uname,
        "password": password,
        "token": data["token"],
        "userId": data["userId"],
        "workspaceId": data["defaultWorkspaceId"],
    }


def _auth(token: str, workspace_id: str | None = None) -> dict:
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


async def _create_policy(test_client: AsyncClient, user: dict, **extra) -> dict:
    body = {
        "name": "HP",
        "startStatuses": ["in_progress"],
        "stopStatuses": ["resolved", "closed"],
        "pauseStatuses": ["feedback"],
        "targetMinutes": 60,
        "notifyAssignee": False,
        "notifyWatchers": False,
        "enabled": True,
        **extra,
    }
    resp = await test_client.post(
        "/api/sla/policies",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_list_and_show_cn_us(test_client: AsyncClient):
    user = await _register(test_client)
    resp = await test_client.get(
        "/api/sla/holiday-packs",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()["data"]["rows"]
    keys = {(r["region"], r["year"]) for r in rows}
    assert ("CN", 2026) in keys and ("US", 2026) in keys

    show = await test_client.get(
        "/api/sla/holiday-packs/CN/2026",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert show.status_code == 200, show.text
    pack = show.json()["data"]
    assert pack["region"] == "CN"
    kinds = {h["kind"] for h in pack["holidays"]}
    assert "closed" in kinds and "forced_open" in kinds

    missing = await test_client.get(
        "/api/sla/holiday-packs/ZZ/2026",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_preview_no_write_apply_ws_pack_wins(test_client: AsyncClient):
    user = await _register(test_client, "e58b")
    # seed a non-pack exception + conflicting National Day kind
    patch_ws = await test_client.patch(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "timezone": "Asia/Shanghai",
            "businessHours": {
                "enabled": True,
                "windows": {
                    **{d: [{"start": "09:00", "end": "18:00"}] for d in ("mon", "tue", "wed", "thu", "fri")},
                    **{d: [] for d in ("sat", "sun")},
                },
                "exceptions": [
                    {"date": "2026-06-01", "kind": "closed"},
                    {"date": "2026-10-01", "kind": "forced_open"},
                ],
            },
        },
    )
    assert patch_ws.status_code == 200, patch_ws.text

    prev = await test_client.post(
        "/api/sla/holiday-packs/CN/2026/preview",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"target": "workspace"},
    )
    assert prev.status_code == 200, prev.text
    pdata = prev.json()["data"]
    assert pdata["countBefore"] == 2
    assert any(x["date"] == "2026-10-01" for x in pdata["replaced"])
    assert any(x["date"] == "2026-06-01" for x in pdata["unchanged"])

    # preview must not write
    get_ws = await test_client.get(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert get_ws.status_code == 200
    ex_before = get_ws.json()["data"]["businessHours"].get("exceptions") or []
    assert len(ex_before) == 2

    apply = await test_client.post(
        "/api/sla/holiday-packs/CN/2026/apply",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"target": "workspace"},
    )
    assert apply.status_code == 200, apply.text
    adata = apply.json()["data"]
    assert adata["countAfter"] > 2
    assert any(r["region"] == "CN" and r["year"] == 2026 for r in adata["appliedHolidayPacks"])

    get_ws2 = await test_client.get(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    bh = get_ws2.json()["data"]["businessHours"]
    by = {e["date"]: e for e in bh["exceptions"]}
    assert by["2026-10-01"]["kind"] == "closed"  # pack wins over forced_open
    assert "2026-06-01" in by  # non-pack kept
    assert "2026-10-10" in by  # makeup forced_open from pack
    assert get_ws2.json()["data"].get("appliedHolidayPacks")


@pytest.mark.asyncio
async def test_apply_policy_materialize_exceptions_overlay(test_client: AsyncClient):
    user = await _register(test_client, "e58c")
    pol = await _create_policy(test_client, user)
    assert pol.get("calendar") in (None, {})

    apply = await test_client.post(
        "/api/sla/holiday-packs/US/2026/apply",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"target": "policy", "policyId": pol["id"]},
    )
    assert apply.status_code == 200, apply.text
    show = await test_client.get(
        "/api/sla/policies",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    row = next(r for r in show.json()["data"]["rows"] if r["id"] == pol["id"])
    assert row["calendar"] and row["calendar"].get("exceptions")
    assert any(e["date"] == "2026-11-26" for e in row["calendar"]["exceptions"])
    assert row.get("appliedHolidayPacks")


@pytest.mark.asyncio
async def test_cross_tenant_policy_404_and_no_extra_webhooks(test_client: AsyncClient):
    a = await _register(test_client, "e58d")
    b = await _register(test_client, "e58e")
    pol_b = await _create_policy(test_client, b)

    resp = await test_client.post(
        "/api/sla/holiday-packs/CN/2026/apply",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"target": "policy", "policyId": pol_b["id"]},
    )
    assert resp.status_code == 404

    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks", new_callable=AsyncMock
    ) as wh:
        ok = await test_client.post(
            "/api/sla/holiday-packs/US/2026/apply",
            headers=_auth(a["token"], a["workspaceId"]),
            json={"target": "workspace"},
        )
        assert ok.status_code == 200, ok.text
        # no new webhook event names from apply path
        for call in wh.await_args_list:
            # fire_webhooks(session, workspace_id=..., event=..., ...)
            kwargs = call.kwargs
            args = call.args
            event = kwargs.get("event") or kwargs.get("event_name")
            if event is None and len(args) >= 3:
                event = args[2]
            if event is not None:
                assert not str(event).startswith("holiday")
