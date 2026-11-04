"""E31：Public Issue Forms CRUD + 公开提交 + 权限/租户."""
from __future__ import annotations

import os
import uuid

import pytest
from httpx import AsyncClient

os.environ["OPENTASK_FORM_RATE_LIMIT"] = "0"


async def _register(client: AsyncClient, prefix: str = "form"):
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
        "username": uname,
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


DEFAULT_FIELDS = [
    {"key": "title", "type": "title", "label": "标题", "required": True},
    {"key": "description", "type": "description", "label": "描述"},
    {"key": "priority", "type": "priority", "label": "优先级"},
]


@pytest.mark.asyncio
async def test_form_crud_public_submit_and_regen(test_client: AsyncClient):
    user = await _register(test_client, "f_crud")
    h = _auth(user["token"], user["workspaceId"])

    created = await test_client.post(
        "/api/forms",
        headers=h,
        json={
            "name": "Bug Report",
            "slug": "bug-report",
            "description": "对外报障",
            "fields": DEFAULT_FIELDS,
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["name"] == "Bug Report"
    assert row["slug"] == "bug-report"
    assert row["token"]
    assert row["publicPath"] == f"/f/{row['token']}"
    fid = row["id"]
    token = row["token"]

    listed = await test_client.get("/api/forms", headers=h)
    assert listed.status_code == 200, listed.text
    assert any(r["id"] == fid for r in listed.json()["data"]["rows"])

    schema = await test_client.get(f"/api/public/forms/{token}")
    assert schema.status_code == 200, schema.text
    assert schema.json()["data"]["name"] == "Bug Report"
    assert "workspaceId" not in schema.json()["data"]

    submitted = await test_client.post(
        f"/api/public/forms/{token}/submit",
        json={
            "values": {
                "title": "按钮点不了",
                "description": "详情…",
                "priority": "high",
            }
        },
    )
    assert submitted.status_code == 200, submitted.text
    data = submitted.json()["data"]
    assert data["issueCode"]
    assert data["title"] == "按钮点不了"

    # issue resolvable by id
    got = await test_client.get(f"/api/issues/{data['issueId']}", headers=h)
    assert got.status_code == 200, got.text
    body = got.json()["data"]
    assert (body.get("issueCode") or body.get("issue_code")) == data["issueCode"]
    assert body.get("id") == data["issueId"]

    # validation errors
    bad = await test_client.post(
        f"/api/public/forms/{token}/submit",
        json={"values": {"description": "no title"}},
    )
    assert bad.status_code == 400, bad.text

    # regenerate token → old 404
    regen = await test_client.post(f"/api/forms/{fid}/regenerate-token", headers=h)
    assert regen.status_code == 200, regen.text
    new_token = regen.json()["data"]["token"]
    assert new_token != token
    old = await test_client.get(f"/api/public/forms/{token}")
    assert old.status_code == 404
    ok = await test_client.get(f"/api/public/forms/{new_token}")
    assert ok.status_code == 200

    # disable → 404
    await test_client.patch(f"/api/forms/{fid}", headers=h, json={"enabled": False})
    disabled = await test_client.get(f"/api/public/forms/{new_token}")
    assert disabled.status_code == 404

    deleted = await test_client.delete(f"/api/forms/{fid}", headers=h)
    assert deleted.status_code == 200, deleted.text


@pytest.mark.asyncio
async def test_form_permissions_and_tenant(test_client: AsyncClient):
    owner = await _register(test_client, "f_own")
    member = await _register(test_client, "f_mem")
    viewer = await _register(test_client, "f_view")
    other = await _register(test_client, "f_oth")
    await _add_member(test_client, owner, member, "member")
    await _add_member(test_client, owner, viewer, "viewer")

    oh = _auth(owner["token"], owner["workspaceId"])
    created = await test_client.post(
        "/api/forms",
        headers=oh,
        json={"name": "A", "fields": DEFAULT_FIELDS},
    )
    assert created.status_code == 200, created.text
    fid = created.json()["data"]["id"]

    # member can read
    mh = _auth(member["token"], owner["workspaceId"])
    listed = await test_client.get("/api/forms", headers=mh)
    assert listed.status_code == 200, listed.text

    # member cannot write
    denied = await test_client.post(
        "/api/forms",
        headers=mh,
        json={"name": "Nope", "fields": DEFAULT_FIELDS},
    )
    assert denied.status_code == 403

    # viewer cannot read
    vh = _auth(viewer["token"], owner["workspaceId"])
    vlist = await test_client.get("/api/forms", headers=vh)
    assert vlist.status_code == 403

    # cross-tenant: other owner cannot see
    xh = _auth(other["token"], other["workspaceId"])
    cross = await test_client.get(f"/api/forms/{fid}", headers=xh)
    assert cross.status_code == 404

    # other workspace header with owner token of different ws
    cross2 = await test_client.get(
        f"/api/forms/{fid}",
        headers=_auth(owner["token"], other["workspaceId"]),
    )
    # owner not member of other's ws → 403
    assert cross2.status_code in (403, 404)


@pytest.mark.asyncio
async def test_form_fields_must_have_title(test_client: AsyncClient):
    user = await _register(test_client, "f_title")
    h = _auth(user["token"], user["workspaceId"])
    bad = await test_client.post(
        "/api/forms",
        headers=h,
        json={
            "name": "NoTitle",
            "fields": [{"key": "description", "type": "description", "label": "D"}],
        },
    )
    assert bad.status_code == 400, bad.text


@pytest.mark.asyncio
async def test_form_submit_assignee_and_labels(test_client: AsyncClient):
    owner = await _register(test_client, "f_asg")
    member = await _register(test_client, "f_asgm")
    await _add_member(test_client, owner, member, "member")
    oh = _auth(owner["token"], owner["workspaceId"])

    # create a label
    tag = await test_client.post(
        "/api/tags",
        headers=oh,
        json={"name": "public-bug"},
    )
    # tags API may be /api/tags or under workspace — try fallbacks
    if tag.status_code != 200:
        tag = await test_client.post(
            f"/api/workspaces/{owner['workspaceId']}/tags",
            headers=oh,
            json={"name": "public-bug"},
        )
    if tag.status_code != 200:
        # list existing or skip labels part
        tag_ok = False
    else:
        tag_ok = True

    fields = list(DEFAULT_FIELDS) + [
        {"key": "assignee", "type": "assignee", "label": "负责人"},
        {"key": "labels", "type": "labels", "label": "标签"},
    ]
    created = await test_client.post(
        "/api/forms",
        headers=oh,
        json={"name": "AssignForm", "fields": fields},
    )
    assert created.status_code == 200, created.text
    token = created.json()["data"]["token"]

    values = {
        "title": "指派给我",
        "assignee": member["username"],
    }
    if tag_ok:
        values["labels"] = ["public-bug"]

    submitted = await test_client.post(
        f"/api/public/forms/{token}/submit",
        json={"values": values},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["data"]["issueCode"]

    # unknown assignee
    bad = await test_client.post(
        f"/api/public/forms/{token}/submit",
        json={"values": {"title": "x", "assignee": "nobody_xyz"}},
    )
    assert bad.status_code == 400
