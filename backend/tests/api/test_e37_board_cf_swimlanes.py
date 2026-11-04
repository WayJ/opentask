"""E37：Board/List CF 泳道 — display prefs / saved views 校验 cf:<key>."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select


async def _register(client: AsyncClient, prefix: str = "e37"):
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


async def _create_cf(
    client: AsyncClient,
    user: dict,
    *,
    name: str,
    key: str,
    type_: str,
    options: list | None = None,
) -> dict:
    body: dict = {"name": name, "key": key, "type": type_}
    if options is not None:
        body["options"] = options
    resp = await client.post(
        "/api/custom-fields",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


DISPLAY_BASE = {
    "view_mode": "board",
    "group_by": "none",
    "swimlane_by": "none",
    "hide_empty_lanes": False,
    "fields": {
        "assignee": True,
        "priority": True,
        "labels": True,
        "estimate_points": True,
        "due_date": False,
        "project": False,
        "cycle": False,
        "issue_code": True,
        "type": False,
    },
}


@pytest.mark.asyncio
async def test_prefs_accept_cf_swimlane_and_merge_keys(test_client: AsyncClient):
    user = await _register(test_client, "e37ok")
    h = _auth(user["token"], user["workspaceId"])
    await _create_cf(
        test_client,
        user,
        name="Severity",
        key="severity",
        type_="single_select",
        options=[{"value": "s1", "label": "S1"}, {"value": "s2", "label": "S2"}],
    )

    put = await test_client.put(
        "/api/display-prefs/issue",
        headers=h,
        json={
            "display": {
                **DISPLAY_BASE,
                "swimlane_by": "cf:severity",
                "custom_field_keys": ["shipped"],
            }
        },
    )
    assert put.status_code == 200, put.text
    display = put.json()["data"]["display"]
    assert display["swimlane_by"] == "cf:severity"
    assert "severity" in display["custom_field_keys"]
    assert "shipped" in display["custom_field_keys"]

    got = await test_client.get("/api/display-prefs/issue", headers=h)
    assert got.status_code == 200, got.text
    assert got.json()["data"]["display"]["swimlane_by"] == "cf:severity"


@pytest.mark.asyncio
async def test_prefs_accept_cf_group_by(test_client: AsyncClient):
    user = await _register(test_client, "e37gb")
    h = _auth(user["token"], user["workspaceId"])
    await _create_cf(
        test_client,
        user,
        name="Area",
        key="area",
        type_="text",
    )
    put = await test_client.put(
        "/api/display-prefs/issue",
        headers=h,
        json={"display": {**DISPLAY_BASE, "view_mode": "list", "group_by": "cf:area"}},
    )
    assert put.status_code == 200, put.text
    display = put.json()["data"]["display"]
    assert display["group_by"] == "cf:area"
    assert "area" in display["custom_field_keys"]


@pytest.mark.asyncio
async def test_prefs_reject_unknown_archived_multiselect_cross_tenant(
    test_client: AsyncClient,
):
    a = await _register(test_client, "e37a")
    b = await _register(test_client, "e37b")
    ha = _auth(a["token"], a["workspaceId"])
    hb = _auth(b["token"], b["workspaceId"])

    # unknown
    bad = await test_client.put(
        "/api/display-prefs/issue",
        headers=ha,
        json={"display": {**DISPLAY_BASE, "swimlane_by": "cf:nosuch"}},
    )
    assert bad.status_code == 400, bad.text

    # multi_select banned
    await _create_cf(
        test_client,
        a,
        name="Tags",
        key="tags",
        type_="multi_select",
        options=[{"value": "a", "label": "A"}],
    )
    ms = await test_client.put(
        "/api/display-prefs/issue",
        headers=ha,
        json={"display": {**DISPLAY_BASE, "swimlane_by": "cf:tags"}},
    )
    assert ms.status_code == 400, ms.text

    # archived
    sev = await _create_cf(
        test_client,
        a,
        name="Sev",
        key="sev",
        type_="single_select",
        options=[{"value": "s1", "label": "S1"}],
    )
    arch = await test_client.patch(
        f"/api/custom-fields/{sev['id']}",
        headers=ha,
        json={"archive": True},
    )
    assert arch.status_code == 200, arch.text
    archived = await test_client.put(
        "/api/display-prefs/issue",
        headers=ha,
        json={"display": {**DISPLAY_BASE, "group_by": "cf:sev"}},
    )
    assert archived.status_code == 400, archived.text

    # cross-tenant same key name: B has severity, A does not → A's cf:severity 400
    await _create_cf(
        test_client,
        b,
        name="Severity",
        key="severity",
        type_="single_select",
        options=[{"value": "s1", "label": "S1"}],
    )
    cross = await test_client.put(
        "/api/display-prefs/issue",
        headers=ha,
        json={"display": {**DISPLAY_BASE, "swimlane_by": "cf:severity"}},
    )
    assert cross.status_code == 400, cross.text

    # B can use own key
    ok_b = await test_client.put(
        "/api/display-prefs/issue",
        headers=hb,
        json={"display": {**DISPLAY_BASE, "swimlane_by": "cf:severity"}},
    )
    assert ok_b.status_code == 200, ok_b.text


@pytest.mark.asyncio
async def test_saved_view_cf_display_roundtrip_and_reject(test_client: AsyncClient):
    user = await _register(test_client, "e37sv")
    h = _auth(user["token"], user["workspaceId"])
    await _create_cf(
        test_client,
        user,
        name="Tier",
        key="tier",
        type_="boolean",
    )

    created = await test_client.post(
        "/api/saved-views",
        headers=h,
        json={
            "name": "By tier",
            "filter": {"tab": "open"},
            "display": {
                "view_mode": "board",
                "swimlane_by": "cf:tier",
                "group_by": "none",
            },
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()["data"]
    assert body["display"]["swimlane_by"] == "cf:tier"
    assert "tier" in (body["display"].get("custom_field_keys") or [])
    view_id = body["id"]

    bad = await test_client.patch(
        f"/api/saved-views/{view_id}",
        headers=h,
        json={"display": {"view_mode": "list", "group_by": "cf:missing"}},
    )
    assert bad.status_code == 400, bad.text


@pytest.mark.asyncio
async def test_prefs_read_falls_back_invalid_cf(test_client: AsyncClient, test_session):
    """ADR D3：读到历史非法 cf: → none（不炸）."""
    from opentask.models.issue_display_prefs.model import IssueDisplayPrefs

    user = await _register(test_client, "e37fb")
    h = _auth(user["token"], user["workspaceId"])

    row = IssueDisplayPrefs(
        workspace_id=user["workspaceId"],
        user_id=str(user["userId"]),
        display_json={
            **DISPLAY_BASE,
            "swimlane_by": "cf:ghost",
            "group_by": "cf:ghost",
        },
    )
    test_session.add(row)
    await test_session.commit()

    got = await test_client.get("/api/display-prefs/issue", headers=h)
    assert got.status_code == 200, got.text
    display = got.json()["data"]["display"]
    assert display["swimlane_by"] == "none"
    assert display["group_by"] == "none"
