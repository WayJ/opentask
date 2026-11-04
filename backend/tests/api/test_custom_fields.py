"""E25：Custom Fields 定义 + Issue 取值 + 跨租户/归档."""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "cf"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str = "cf-issue") -> dict:
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": title, "type": "feature", "status": "open", "priority": "medium"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_custom_field_crud_and_slug(test_client: AsyncClient):
    user = await _register(test_client, "cf_crud")
    h = _auth(user["token"], user["workspaceId"])

    created = await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "Severity",
            "type": "single_select",
            "options": [{"value": "s1", "label": "S1"}, {"value": "s2", "label": "S2"}],
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["key"] == "severity"
    assert row["type"] == "single_select"
    assert len(row["options"]) == 2
    fid = row["id"]

    listed = await test_client.get("/api/custom-fields", headers=h)
    assert listed.status_code == 200, listed.text
    assert any(r["id"] == fid for r in listed.json()["data"]["rows"])

    patched = await test_client.patch(
        f"/api/custom-fields/{fid}",
        headers=h,
        json={"name": "严重度", "position": 2},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["name"] == "严重度"
    assert patched.json()["data"]["key"] == "severity"

    deleted = await test_client.delete(f"/api/custom-fields/{fid}", headers=h)
    assert deleted.status_code == 200, deleted.text
    missing = await test_client.get(f"/api/custom-fields/{fid}", headers=h)
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_custom_field_duplicate_key(test_client: AsyncClient):
    user = await _register(test_client, "cf_dup")
    h = _auth(user["token"], user["workspaceId"])
    r1 = await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={"name": "A", "key": "team", "type": "text"},
    )
    assert r1.status_code == 200, r1.text
    r2 = await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={"name": "B", "key": "team", "type": "text"},
    )
    assert r2.status_code in (400, 409), r2.text


@pytest.mark.asyncio
async def test_custom_field_viewer_read_ok_write_forbidden(test_client: AsyncClient):
    owner = await _register(test_client, "cf_own")
    viewer = await _register(test_client, "cf_view")
    await _add_member(test_client, owner, viewer, role="viewer")
    oh = _auth(owner["token"], owner["workspaceId"])
    vh = _auth(viewer["token"], owner["workspaceId"])

    created = await test_client.post(
        "/api/custom-fields",
        headers=oh,
        json={"name": "Region", "type": "text"},
    )
    assert created.status_code == 200, created.text
    fid = created.json()["data"]["id"]

    listed = await test_client.get("/api/custom-fields", headers=vh)
    assert listed.status_code == 200, listed.text

    forbidden = await test_client.post(
        "/api/custom-fields",
        headers=vh,
        json={"name": "Nope", "type": "text"},
    )
    assert forbidden.status_code == 403, forbidden.text

    patch_f = await test_client.patch(
        f"/api/custom-fields/{fid}", headers=vh, json={"name": "X"}
    )
    assert patch_f.status_code == 403


@pytest.mark.asyncio
async def test_custom_field_cross_tenant(test_client: AsyncClient):
    a = await _register(test_client, "cf_a")
    b = await _register(test_client, "cf_b")
    ah = _auth(a["token"], a["workspaceId"])
    bh = _auth(b["token"], b["workspaceId"])

    created = await test_client.post(
        "/api/custom-fields", headers=ah, json={"name": "Secret", "type": "text"}
    )
    assert created.status_code == 200, created.text
    fid = created.json()["data"]["id"]

    got = await test_client.get(f"/api/custom-fields/{fid}", headers=bh)
    assert got.status_code == 404, got.text

    # missing workspace header rejected by deps
    no_ws = await test_client.get(
        "/api/custom-fields",
        headers={"Authorization": f"Bearer {a['token']}"},
    )
    assert no_ws.status_code in (400, 403, 422), no_ws.text


@pytest.mark.asyncio
async def test_issue_custom_fields_type_validation_and_detail(test_client: AsyncClient):
    user = await _register(test_client, "cf_val")
    h = _auth(user["token"], user["workspaceId"])

    text_f = (
        await test_client.post(
            "/api/custom-fields", headers=h, json={"name": "Note", "key": "note", "type": "text"}
        )
    ).json()["data"]
    num_f = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={"name": "Score", "key": "score", "type": "number"},
        )
    ).json()["data"]
    bool_f = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={"name": "VIP", "key": "vip", "type": "boolean"},
        )
    ).json()["data"]
    date_f = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={"name": "Launch", "key": "launch", "type": "date"},
        )
    ).json()["data"]
    sel_f = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={
                "name": "Tier",
                "key": "tier",
                "type": "single_select",
                "options": ["gold", "silver"],
            },
        )
    ).json()["data"]
    multi_f = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={
                "name": "TagsCF",
                "key": "cf_tags",
                "type": "multi_select",
                "options": [{"value": "a", "label": "A"}, {"value": "b", "label": "B"}],
            },
        )
    ).json()["data"]

    issue = await _create_issue(test_client, user)
    iid = issue["id"]

    bad = await test_client.patch(
        f"/api/issues/{iid}/custom-fields",
        headers=h,
        json={"values": [{"key": "score", "value": "not-a-number"}]},
    )
    assert bad.status_code == 400, bad.text

    bad_date = await test_client.patch(
        f"/api/issues/{iid}/custom-fields",
        headers=h,
        json={"values": [{"key": "launch", "value": "2026/01/01"}]},
    )
    assert bad_date.status_code == 400, bad_date.text

    bad_sel = await test_client.patch(
        f"/api/issues/{iid}/custom-fields",
        headers=h,
        json={"values": [{"key": "tier", "value": "bronze"}]},
    )
    assert bad_sel.status_code == 400, bad_sel.text

    ok = await test_client.patch(
        f"/api/issues/{iid}/custom-fields",
        headers=h,
        json={
            "values": [
                {"fieldId": text_f["id"], "value": "hello"},
                {"key": "score", "value": 9.5},
                {"key": "vip", "value": True},
                {"key": "launch", "value": "2026-11-04"},
                {"key": "tier", "value": "gold"},
                {"key": "cf_tags", "value": ["a", "b"]},
            ]
        },
    )
    assert ok.status_code == 200, ok.text
    cfs = ok.json()["data"]["customFields"]
    by_key = {c["key"]: c["value"] for c in cfs}
    assert by_key["note"] == "hello"
    assert by_key["score"] == 9.5
    assert by_key["vip"] is True
    assert by_key["launch"] == "2026-11-04"
    assert by_key["tier"] == "gold"
    assert by_key["cf_tags"] == ["a", "b"]

    detail = await test_client.get(f"/api/issues/{iid}", headers=h)
    assert detail.status_code == 200, detail.text
    dcf = detail.json()["data"].get("customFields")
    assert isinstance(dcf, list)
    assert any(c["key"] == "note" and c["value"] == "hello" for c in dcf)

    # list default without customFields
    listed = await test_client.get("/api/issues", headers=h)
    assert listed.status_code == 200, listed.text
    row0 = next(r for r in listed.json()["data"]["rows"] if r["id"] == iid)
    assert "customFields" not in row0

    listed_inc = await test_client.get(
        "/api/issues", headers=h, params={"include": "custom_fields"}
    )
    assert listed_inc.status_code == 200, listed_inc.text
    row1 = next(r for r in listed_inc.json()["data"]["rows"] if r["id"] == iid)
    assert "customFields" in row1
    assert any(c["key"] == "note" for c in row1["customFields"])

    # clear value
    cleared = await test_client.patch(
        f"/api/issues/{iid}/custom-fields",
        headers=h,
        json={"values": [{"key": "note", "value": None}]},
    )
    assert cleared.status_code == 200, cleared.text
    by_key2 = {c["key"]: c["value"] for c in cleared.json()["data"]["customFields"]}
    assert by_key2.get("note") is None


@pytest.mark.asyncio
async def test_archive_preferred_over_hard_delete(test_client: AsyncClient):
    user = await _register(test_client, "cf_arch")
    h = _auth(user["token"], user["workspaceId"])
    field = (
        await test_client.post(
            "/api/custom-fields", headers=h, json={"name": "Legacy", "key": "legacy", "type": "text"}
        )
    ).json()["data"]
    issue = await _create_issue(test_client, user)
    await test_client.patch(
        f"/api/issues/{issue['id']}/custom-fields",
        headers=h,
        json={"values": [{"key": "legacy", "value": "keep"}]},
    )

    hard = await test_client.delete(f"/api/custom-fields/{field['id']}", headers=h)
    assert hard.status_code == 409, hard.text

    archived = await test_client.patch(
        f"/api/custom-fields/{field['id']}",
        headers=h,
        json={"archive": True},
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["data"]["archivedAt"] is not None

    # default list hides archived
    listed = await test_client.get("/api/custom-fields", headers=h)
    assert all(r["id"] != field["id"] for r in listed.json()["data"]["rows"])

    with_arch = await test_client.get(
        "/api/custom-fields", headers=h, params={"includeArchived": True}
    )
    assert any(r["id"] == field["id"] for r in with_arch.json()["data"]["rows"])

    # write to archived field forbidden
    write = await test_client.patch(
        f"/api/issues/{issue['id']}/custom-fields",
        headers=h,
        json={"values": [{"key": "legacy", "value": "new"}]},
    )
    assert write.status_code == 400, write.text

    # detail still shows historical value
    detail = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    cfs = detail.json()["data"]["customFields"]
    assert any(c["key"] == "legacy" and c["value"] == "keep" for c in cfs)


@pytest.mark.asyncio
async def test_issue_custom_fields_cross_tenant(test_client: AsyncClient):
    a = await _register(test_client, "cf_ia")
    b = await _register(test_client, "cf_ib")
    ah = _auth(a["token"], a["workspaceId"])
    bh = _auth(b["token"], b["workspaceId"])
    field = (
        await test_client.post(
            "/api/custom-fields", headers=ah, json={"name": "OnlyA", "key": "only_a", "type": "text"}
        )
    ).json()["data"]
    issue_a = await _create_issue(test_client, a)
    issue_b = await _create_issue(test_client, b)

    # B cannot patch A's issue
    cross = await test_client.patch(
        f"/api/issues/{issue_a['id']}/custom-fields",
        headers=bh,
        json={"values": [{"key": "only_a", "value": "x"}]},
    )
    assert cross.status_code in (403, 404), cross.text

    # B cannot use A's field id on B's issue (field not in B workspace)
    bad_field = await test_client.patch(
        f"/api/issues/{issue_b['id']}/custom-fields",
        headers=bh,
        json={"values": [{"fieldId": field["id"], "value": "x"}]},
    )
    assert bad_field.status_code == 404, bad_field.text
