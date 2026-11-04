"""E32：Issue list 按自定义字段过滤（cf.<key> / cf=key=value）."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e32"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str) -> dict:
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": title, "type": "feature", "status": "open", "priority": "medium"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_parse_helpers_unit():
    from opentask.services.custom_field.service import parse_cf_query_items

    items = parse_cf_query_items(
        [
            ("cf.severity", "s1"),
            ("cf", "env=prod"),
            ("status", "open"),
            ("cf", "bad"),
            ("cf.", "x"),
        ]
    )
    assert items == [("severity", "s1"), ("env", "prod")]


@pytest.mark.asyncio
async def test_list_filter_cf_dot_and_types(test_client: AsyncClient):
    user = await _register(test_client, "e32f")
    h = _auth(user["token"], user["workspaceId"])

    sev = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={
                "name": "Severity",
                "key": "severity",
                "type": "single_select",
                "options": [{"value": "s1", "label": "S1"}, {"value": "s2", "label": "S2"}],
            },
        )
    ).json()["data"]
    flag = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={"name": "Shipped", "key": "shipped", "type": "boolean"},
        )
    ).json()["data"]
    tags = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={
                "name": "Stack",
                "key": "stack",
                "type": "multi_select",
                "options": [
                    {"value": "fe", "label": "FE"},
                    {"value": "be", "label": "BE"},
                ],
            },
        )
    ).json()["data"]

    a = await _create_issue(test_client, user, "A-s1")
    b = await _create_issue(test_client, user, "B-s2")
    c = await _create_issue(test_client, user, "C-multi")

    assert (
        await test_client.patch(
            f"/api/issues/{a['id']}/custom-fields",
            headers=h,
            json={"values": [{"key": "severity", "value": "s1"}, {"key": "shipped", "value": True}]},
        )
    ).status_code == 200
    assert (
        await test_client.patch(
            f"/api/issues/{b['id']}/custom-fields",
            headers=h,
            json={"values": [{"key": "severity", "value": "s2"}, {"key": "shipped", "value": False}]},
        )
    ).status_code == 200
    assert (
        await test_client.patch(
            f"/api/issues/{c['id']}/custom-fields",
            headers=h,
            json={"values": [{"key": "stack", "value": ["fe", "be"]}]},
        )
    ).status_code == 200

    # cf.severity=s1
    r = await test_client.get("/api/issues", headers=h, params={"cf.severity": "s1", "page_size": 50})
    assert r.status_code == 200, r.text
    ids = {row["id"] for row in r.json()["data"]["rows"]}
    assert a["id"] in ids
    assert b["id"] not in ids

    # boolean true
    r = await test_client.get("/api/issues", headers=h, params={"cf.shipped": "true", "page_size": 50})
    ids = {row["id"] for row in r.json()["data"]["rows"]}
    assert a["id"] in ids
    assert b["id"] not in ids

    # multi contains
    r = await test_client.get("/api/issues", headers=h, params={"cf.stack": "fe", "page_size": 50})
    ids = {row["id"] for row in r.json()["data"]["rows"]}
    assert c["id"] in ids
    assert a["id"] not in ids

    # repeated cf=key=value form
    r = await test_client.get(
        "/api/issues",
        headers=h,
        params=[("cf", "severity=s2"), ("page_size", "50")],
    )
    assert r.status_code == 200, r.text
    ids = {row["id"] for row in r.json()["data"]["rows"]}
    assert b["id"] in ids
    assert a["id"] not in ids

    # AND: severity=s1 + shipped=true
    r = await test_client.get(
        "/api/issues",
        headers=h,
        params={"cf.severity": "s1", "cf.shipped": "1", "page_size": 50},
    )
    ids = {row["id"] for row in r.json()["data"]["rows"]}
    assert ids == {a["id"]} or a["id"] in ids

    # unknown key → empty
    r = await test_client.get(
        "/api/issues", headers=h, params={"cf.no_such_field": "x", "page_size": 50}
    )
    assert r.status_code == 200
    assert r.json()["data"]["rows"] == []
    assert r.json()["data"]["total"] == 0

    # include=custom_fields still works with filter
    r = await test_client.get(
        "/api/issues",
        headers=h,
        params={"cf.severity": "s1", "include": "custom_fields", "page_size": 50},
    )
    assert r.status_code == 200
    rows = r.json()["data"]["rows"]
    assert len(rows) >= 1
    assert "customFields" in rows[0]
    assert sev["id"] and flag["id"] and tags["id"]


@pytest.mark.asyncio
async def test_cf_filter_cross_tenant_empty(test_client: AsyncClient):
    owner = await _register(test_client, "e32o")
    other = await _register(test_client, "e32x")
    h_owner = _auth(owner["token"], owner["workspaceId"])
    h_other = _auth(other["token"], other["workspaceId"])

    await test_client.post(
        "/api/custom-fields",
        headers=h_owner,
        json={"name": "Team", "key": "team", "type": "text"},
    )
    issue = await _create_issue(test_client, owner, "tenant-a")
    await test_client.patch(
        f"/api/issues/{issue['id']}/custom-fields",
        headers=h_owner,
        json={"values": [{"key": "team", "value": "alpha"}]},
    )

    # other workspace: same key name does not exist → empty (not leak)
    r = await test_client.get(
        "/api/issues", headers=h_other, params={"cf.team": "alpha", "page_size": 50}
    )
    assert r.status_code == 200
    assert r.json()["data"]["rows"] == []

    # other cannot see owner's issue even without filter via wrong WS header
    r2 = await test_client.get(
        "/api/issues",
        headers=_auth(other["token"], owner["workspaceId"]),
        params={"cf.team": "alpha"},
    )
    assert r2.status_code in (403, 404)
