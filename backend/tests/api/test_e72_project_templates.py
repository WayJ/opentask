"""E72: project_templates CRUD + apply + from-project."""
from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "pt"):
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


@pytest.mark.asyncio
async def test_crud_and_name_conflict(test_client: AsyncClient):
    user = await _register(test_client, "pt_crud")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post(
        "/api/project-templates",
        headers=h,
        json={
            "name": "Launch Kit",
            "description": "std",
            "payload": {
                "milestones": [
                    {"name": "Kickoff", "targetOffsetDays": 0},
                    {"name": "GA", "targetOffsetDays": 45},
                ]
            },
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["name"] == "Launch Kit"
    assert len(row["payload"]["milestones"]) == 2

    dup = await test_client.post(
        "/api/project-templates",
        headers=h,
        json={"name": "Launch Kit", "payload": {"milestones": []}},
    )
    assert dup.status_code == 409

    listed = await test_client.get("/api/project-templates", headers=h)
    assert listed.status_code == 200
    assert listed.json()["data"]["total"] >= 1

    shown = await test_client.get(f"/api/project-templates/{row['id']}", headers=h)
    assert shown.status_code == 200
    assert shown.json()["data"]["id"] == row["id"]

    patched = await test_client.patch(
        f"/api/project-templates/{row['id']}",
        headers=h,
        json={"description": "updated"},
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["description"] == "updated"

    deleted = await test_client.delete(f"/api/project-templates/{row['id']}", headers=h)
    assert deleted.status_code == 200
    gone = await test_client.get(f"/api/project-templates/{row['id']}", headers=h)
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_apply_seeds_milestones_zero_issues(test_client: AsyncClient):
    user = await _register(test_client, "pt_apply")
    h = _auth(user["token"], user["workspaceId"])
    tpl = (
        await test_client.post(
            "/api/project-templates",
            headers=h,
            json={
                "name": "Two Mile",
                "payload": {
                    "description": "from tpl",
                    "milestones": [
                        {"name": "Kickoff", "targetOffsetDays": 0},
                        {"name": "Beta", "targetOffsetDays": 30},
                    ],
                },
            },
        )
    ).json()["data"]

    starts = "2026-03-01T00:00:00"
    applied = await test_client.post(
        f"/api/project-templates/{tpl['id']}/apply",
        headers=h,
        json={"name": "Proj From Tpl", "startsAt": starts},
    )
    assert applied.status_code == 200, applied.text
    data = applied.json()["data"]
    assert data["project"]["name"] == "Proj From Tpl"
    # description from payload when body omits
    assert data["project"]["description"] == "from tpl"
    miles = data["milestones"]
    assert len(miles) == 2
    d0 = datetime.fromisoformat(str(miles[0]["target_date"]).replace("Z", "")).date()
    d1 = datetime.fromisoformat(str(miles[1]["target_date"]).replace("Z", "")).date()
    assert (d1 - d0).days == 30

    # via create + template_id
    created = await test_client.post(
        "/api/projects",
        headers=h,
        json={"name": "Via Create", "template_id": tpl["id"], "starts_at": starts},
    )
    assert created.status_code == 200, created.text
    proj = created.json()["data"]
    assert proj["name"] == "Via Create"
    listed_m = await test_client.get(
        f"/api/projects/{proj['id']}/milestones", headers=h
    )
    assert listed_m.status_code == 200, listed_m.text
    assert len(listed_m.json()["data"]) == 2

    # Issues for applied project stay 0
    pid = data["project"]["id"]
    issues = await test_client.get(
        "/api/issues",
        headers=h,
        params={"project_id": pid},
    )
    assert issues.status_code == 200, issues.text
    issue_data = issues.json()["data"]
    rows = issue_data.get("rows") if isinstance(issue_data, dict) else issue_data
    assert (rows or []) == [] or len(rows or []) == 0


@pytest.mark.asyncio
async def test_milestones_31_rejected(test_client: AsyncClient):
    user = await _register(test_client, "pt_cap")
    h = _auth(user["token"], user["workspaceId"])
    resp = await test_client.post(
        "/api/project-templates",
        headers=h,
        json={
            "name": "Too Many",
            "payload": {"milestones": [{"name": f"M{i}"} for i in range(31)]},
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_from_project_roundtrip(test_client: AsyncClient):
    user = await _register(test_client, "pt_fp")
    h = _auth(user["token"], user["workspaceId"])
    proj = (
        await test_client.post(
            "/api/projects",
            headers=h,
            json={"name": "Src", "description": "d"},
        )
    ).json()["data"]
    await test_client.put(
        f"/api/projects/{proj['id']}",
        headers=h,
        json={"starts_at": "2026-01-01T00:00:00"},
    )
    await test_client.post(
        f"/api/projects/{proj['id']}/milestones",
        headers=h,
        json={"name": "A", "target_date": "2026-01-01T00:00:00", "position": 0},
    )
    await test_client.post(
        f"/api/projects/{proj['id']}/milestones",
        headers=h,
        json={"name": "B", "target_date": "2026-01-31T00:00:00", "position": 1},
    )
    await test_client.post(
        f"/api/projects/{proj['id']}/milestones",
        headers=h,
        json={"name": "C", "position": 2},
    )
    saved = await test_client.post(
        f"/api/project-templates/from-project/{proj['id']}",
        headers=h,
        json={"name": "From Src"},
    )
    assert saved.status_code == 200, saved.text
    payload = saved.json()["data"]["payload"]
    assert len(payload["milestones"]) == 3
    assert payload["milestones"][1]["targetOffsetDays"] == 30

    # re-apply gets isomorphic skeleton
    applied = await test_client.post(
        f"/api/project-templates/{saved.json()['data']['id']}/apply",
        headers=h,
        json={"name": "Clone", "startsAt": "2026-01-01T00:00:00"},
    )
    assert applied.status_code == 200, applied.text
    assert len(applied.json()["data"]["milestones"]) == 3


@pytest.mark.asyncio
async def test_cross_ws_404_and_viewer_403(test_client: AsyncClient):
    owner = await _register(test_client, "pt_o")
    other = await _register(test_client, "pt_x")
    viewer = await _register(test_client, "pt_v")
    await _add_member(test_client, owner, viewer, role="viewer")
    h = _auth(owner["token"], owner["workspaceId"])
    tpl = (
        await test_client.post(
            "/api/project-templates",
            headers=h,
            json={"name": "Priv", "payload": {"milestones": []}},
        )
    ).json()["data"]
    cross = await test_client.get(
        f"/api/project-templates/{tpl['id']}",
        headers=_auth(other["token"], other["workspaceId"]),
    )
    assert cross.status_code == 404
    denied = await test_client.post(
        "/api/project-templates",
        headers=_auth(viewer["token"], owner["workspaceId"]),
        json={"name": "Nope", "payload": {"milestones": []}},
    )
    assert denied.status_code == 403
