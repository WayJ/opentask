"""E64: holiday packs expansion — list filter + apply EU + no-emit."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(test_client: AsyncClient, prefix: str = "e64"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
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


@pytest.mark.asyncio
async def test_list_includes_e64_keys_and_filter(test_client: AsyncClient):
    user = await _register(test_client)
    resp = await test_client.get(
        "/api/sla/holiday-packs",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()["data"]["rows"]
    keys = {(r["region"], r["year"]) for r in rows}
    for key in (
        ("CN", 2026),
        ("US", 2026),
        ("EU", 2026),
        ("UK", 2026),
        ("CN", 2027),
        ("US", 2027),
        ("EU", 2027),
        ("UK", 2027),
    ):
        assert key in keys

    filtered = await test_client.get(
        "/api/sla/holiday-packs",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"region": "UK", "year": 2026},
    )
    assert filtered.status_code == 200, filtered.text
    frows = filtered.json()["data"]["rows"]
    assert len(frows) == 1 and frows[0]["region"] == "UK" and frows[0]["year"] == 2026

    eu = await test_client.get(
        "/api/sla/holiday-packs/EU/2026",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert eu.status_code == 200, eu.text
    assert all(h["kind"] == "closed" for h in eu.json()["data"]["holidays"])


@pytest.mark.asyncio
async def test_apply_eu_2026_ws_and_no_emit(test_client: AsyncClient):
    user = await _register(test_client, "e64b")
    with (
        patch("opentask.services.workspace_webhook.service.fire_webhooks", new_callable=AsyncMock) as wh,
        patch("opentask.services.automation.service.fire_automations", new_callable=AsyncMock) as auto,
    ):
        wh.return_value = None
        auto.return_value = None
        apply = await test_client.post(
            "/api/sla/holiday-packs/EU/2026/apply",
            headers=_auth(user["token"], user["workspaceId"]),
            json={"target": "workspace"},
        )
        assert apply.status_code == 200, apply.text
        adata = apply.json()["data"]
        assert adata["countAfter"] >= 10
        assert any(r["region"] == "EU" and r["year"] == 2026 for r in adata["appliedHolidayPacks"])
        for call in wh.await_args_list:
            kwargs = call.kwargs
            args = call.args
            event = kwargs.get("event") or kwargs.get("event_name")
            if event is None and len(args) >= 3:
                event = args[2]
            if event is not None:
                assert not str(event).startswith("holiday")
        # formula/automation path must not be newly fired by pack apply
        assert auto.await_count == 0

    get_ws = await test_client.get(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert get_ws.status_code == 200
    by = {e["date"]: e for e in (get_ws.json()["data"]["businessHours"].get("exceptions") or [])}
    assert by["2026-05-01"]["kind"] == "closed"
    assert by["2026-12-25"]["kind"] == "closed"


@pytest.mark.asyncio
async def test_cn_2026_regression_still_listed(test_client: AsyncClient):
    user = await _register(test_client, "e64c")
    show = await test_client.get(
        "/api/sla/holiday-packs/CN/2026",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert show.status_code == 200
    kinds = {h["kind"] for h in show.json()["data"]["holidays"]}
    assert "closed" in kinds and "forced_open" in kinds
