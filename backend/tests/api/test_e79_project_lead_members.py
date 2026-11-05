"""E79: Project lead + members mid (roster-only) — no ACL change."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e79"):
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


async def _add_member(client: AsyncClient, owner: dict, member: dict, role: str = "member"):
    resp = await client.post(
        f"/api/workspaces/{owner['workspaceId']}/members",
        headers=_auth(owner["token"]),
        json={"userId": member["userId"], "role": role},
    )
    assert resp.status_code == 200, resp.text


async def _create_project(client: AsyncClient, user: dict, name: str | None = None) -> dict:
    resp = await client.post(
        "/api/projects",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name or f"E79-{uuid.uuid4().hex[:6]}", "description": "e79"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_set_lead_upserts_member_and_show_fields(test_client: AsyncClient):
    owner = await _register(test_client, "e79_sl")
    lead = await _register(test_client, "e79_lead")
    await _add_member(test_client, owner, lead)
    h = _auth(owner["token"], owner["workspaceId"])
    project = await _create_project(test_client, owner)

    resp = await test_client.patch(
        f"/api/projects/{project['id']}",
        headers=h,
        json={"lead_id": lead["userId"]},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["lead_id"] == lead["userId"]
    assert data.get("lead") and data["lead"]["id"] == lead["userId"]
    member_ids = [m["id"] for m in (data.get("members") or [])]
    assert lead["userId"] in member_ids

    listed = await test_client.get("/api/projects", headers=h)
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]
    row = next(r for r in rows if r["id"] == project["id"])
    assert row["lead_id"] == lead["userId"]
    assert row.get("member_count", 0) >= 1
    assert "members" not in row or row.get("members") is None


@pytest.mark.asyncio
async def test_clear_lead_keeps_member_row(test_client: AsyncClient):
    owner = await _register(test_client, "e79_cl")
    lead = await _register(test_client, "e79_cl_u")
    await _add_member(test_client, owner, lead)
    h = _auth(owner["token"], owner["workspaceId"])
    project = await _create_project(test_client, owner)

    await test_client.patch(
        f"/api/projects/{project['id']}",
        headers=h,
        json={"lead_id": lead["userId"]},
    )
    cleared = await test_client.patch(
        f"/api/projects/{project['id']}",
        headers=h,
        json={"lead_id": None},
    )
    assert cleared.status_code == 200, cleared.text
    data = cleared.json()["data"]
    assert data["lead_id"] is None
    assert data.get("lead") is None
    member_ids = [m["id"] for m in (data.get("members") or [])]
    assert lead["userId"] in member_ids


@pytest.mark.asyncio
async def test_member_add_remove_idempotent_and_cross_ws_rejected(test_client: AsyncClient):
    owner = await _register(test_client, "e79_m")
    mate = await _register(test_client, "e79_mm")
    outsider = await _register(test_client, "e79_out")
    await _add_member(test_client, owner, mate)
    h = _auth(owner["token"], owner["workspaceId"])
    project = await _create_project(test_client, owner)

    r1 = await test_client.post(
        f"/api/projects/{project['id']}/members",
        headers=h,
        json={"user_id": mate["userId"]},
    )
    assert r1.status_code == 200, r1.text
    r2 = await test_client.post(
        f"/api/projects/{project['id']}/members",
        headers=h,
        json={"user_id": mate["userId"]},
    )
    assert r2.status_code == 200, r2.text

    listed = await test_client.get(
        f"/api/projects/{project['id']}/members",
        headers=h,
    )
    assert listed.status_code == 200, listed.text
    ids = [m["id"] for m in listed.json()["data"]]
    assert ids.count(mate["userId"]) == 1

    bad = await test_client.post(
        f"/api/projects/{project['id']}/members",
        headers=h,
        json={"user_id": outsider["userId"]},
    )
    assert bad.status_code == 400, bad.text

    rm = await test_client.delete(
        f"/api/projects/{project['id']}/members/{mate['userId']}",
        headers=h,
    )
    assert rm.status_code == 200, rm.text
    listed2 = await test_client.get(
        f"/api/projects/{project['id']}/members",
        headers=h,
    )
    ids2 = [m["id"] for m in listed2.json()["data"]]
    assert mate["userId"] not in ids2


@pytest.mark.asyncio
async def test_viewer_write_forbidden_cross_tenant_404(test_client: AsyncClient):
    owner = await _register(test_client, "e79_v")
    viewer = await _register(test_client, "e79_vv")
    other = await _register(test_client, "e79_other")
    await _add_member(test_client, owner, viewer, role="viewer")
    h_owner = _auth(owner["token"], owner["workspaceId"])
    h_viewer = _auth(viewer["token"], owner["workspaceId"])
    project = await _create_project(test_client, owner)

    forbidden = await test_client.patch(
        f"/api/projects/{project['id']}",
        headers=h_viewer,
        json={"lead_id": owner["userId"]},
    )
    assert forbidden.status_code == 403, forbidden.text

    forbidden_m = await test_client.post(
        f"/api/projects/{project['id']}/members",
        headers=h_viewer,
        json={"user_id": owner["userId"]},
    )
    assert forbidden_m.status_code == 403, forbidden_m.text

    # cross-tenant: other WS user hitting owner's project with their own WS header → 404
    h_other = _auth(other["token"], other["workspaceId"])
    missing = await test_client.get(
        f"/api/projects/{project['id']}/members",
        headers=h_other,
    )
    assert missing.status_code == 404, missing.text


@pytest.mark.asyncio
async def test_no_new_webhook_name_and_acl_unchanged(test_client: AsyncClient):
    owner = await _register(test_client, "e79_wh")
    mate = await _register(test_client, "e79_wh_m")
    await _add_member(test_client, owner, mate)
    h = _auth(owner["token"], owner["workspaceId"])
    project = await _create_project(test_client, owner)

    # Non-member of project roster can still read project (ACL unchanged — WS membership only)
    show = await test_client.get(
        f"/api/projects/{project['id']}",
        headers=_auth(mate["token"], owner["workspaceId"]),
    )
    assert show.status_code == 200, show.text

    with patch(
        "opentask.services.workspace_webhook.service.WorkspaceWebhookService.dispatch",
        new_callable=AsyncMock,
        create=True,
    ) as dispatch_spy:
        ok = await test_client.patch(
            f"/api/projects/{project['id']}",
            headers=h,
            json={"lead_id": mate["userId"]},
        )
        assert ok.status_code == 200, ok.text
        await test_client.post(
            f"/api/projects/{project['id']}/members",
            headers=h,
            json={"user_id": owner["userId"]},
        )
        for call in dispatch_spy.await_args_list:
            args = call.args + tuple(call.kwargs.values())
            flat = " ".join(str(a) for a in args)
            assert "project.lead" not in flat
            assert "project.member" not in flat
            assert "lead_changed" not in flat


@pytest.mark.asyncio
async def test_e72_template_apply_untouched():
    """E79 must not rewrite E72 template apply / template schema for lead."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[2] / "opentask"
    apply_src = (root / "services" / "project_template" / "service.py").read_text(encoding="utf-8")
    assert "lead_id" not in apply_src
    assert "project_members" not in apply_src
