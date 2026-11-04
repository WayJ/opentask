"""E10-S2：Initiative healthSummary rollup from Project.health_status"""
from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "ih"):
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


async def _create_project(client: AsyncClient, user: dict, name: str | None = None) -> dict:
    resp = await client.post(
        "/api/projects",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name or f"Proj-{uuid.uuid4().hex[:6]}", "description": "ih"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _set_health(client: AsyncClient, user: dict, project_id: str, status: str):
    resp = await client.post(
        f"/api/projects/{project_id}/health",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"status": status, "note": f"set {status}"},
    )
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_health_empty_projects(test_client: AsyncClient):
    user = await _register(test_client, "ih_empty")
    h = _auth(user["token"], user["workspaceId"])
    created = await test_client.post("/api/initiatives", headers=h, json={"name": "空"})
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    hs = row["healthSummary"]
    assert hs["overall"] is None
    assert hs["projectCount"] == 0
    assert hs["counts"] == {"onTrack": 0, "atRisk": 0, "offTrack": 0, "unknown": 0}

    got = await test_client.get(f"/api/initiatives/{row['id']}", headers=h)
    assert got.status_code == 200
    assert got.json()["data"]["healthSummary"]["projectCount"] == 0


@pytest.mark.asyncio
async def test_health_worst_of_mixed(test_client: AsyncClient):
    user = await _register(test_client, "ih_mix")
    h = _auth(user["token"], user["workspaceId"])
    p1 = await _create_project(test_client, user, "OK")
    p2 = await _create_project(test_client, user, "Risk")
    await _set_health(test_client, user, p1["id"], "on_track")
    await _set_health(test_client, user, p2["id"], "at_risk")

    created = await test_client.post(
        "/api/initiatives",
        headers=h,
        json={"name": "混合", "projectIds": [p1["id"], p2["id"]]},
    )
    assert created.status_code == 200, created.text
    hs = created.json()["data"]["healthSummary"]
    assert hs["overall"] == "at_risk"
    assert hs["projectCount"] == 2
    assert hs["counts"]["onTrack"] == 1
    assert hs["counts"]["atRisk"] == 1
    assert hs["counts"]["offTrack"] == 0
    assert hs["counts"]["unknown"] == 0


@pytest.mark.asyncio
async def test_health_off_track_dominates(test_client: AsyncClient):
    user = await _register(test_client, "ih_off")
    h = _auth(user["token"], user["workspaceId"])
    p1 = await _create_project(test_client, user, "A")
    p2 = await _create_project(test_client, user, "B")
    await _set_health(test_client, user, p1["id"], "on_track")
    await _set_health(test_client, user, p2["id"], "off_track")

    created = await test_client.post(
        "/api/initiatives",
        headers=h,
        json={"name": "崩溃", "projectIds": [p1["id"], p2["id"]]},
    )
    assert created.status_code == 200, created.text
    assert created.json()["data"]["healthSummary"]["overall"] == "off_track"
    assert created.json()["data"]["healthSummary"]["counts"]["offTrack"] == 1


@pytest.mark.asyncio
async def test_health_all_unknown(test_client: AsyncClient):
    user = await _register(test_client, "ih_unk")
    h = _auth(user["token"], user["workspaceId"])
    p1 = await _create_project(test_client, user, "U1")
    p2 = await _create_project(test_client, user, "U2")
    # no health set → null
    created = await test_client.post(
        "/api/initiatives",
        headers=h,
        json={"name": "未知", "projectIds": [p1["id"], p2["id"]]},
    )
    assert created.status_code == 200, created.text
    hs = created.json()["data"]["healthSummary"]
    assert hs["overall"] is None
    assert hs["projectCount"] == 2
    assert hs["counts"]["unknown"] == 2

    detail = await test_client.get(f"/api/initiatives/{created.json()['data']['id']}", headers=h)
    assert detail.status_code == 200
    projects = detail.json()["data"].get("projects") or []
    assert len(projects) == 2
    assert all(p.get("healthStatus") is None for p in projects)


@pytest.mark.asyncio
async def test_list_includes_health_summary(test_client: AsyncClient):
    user = await _register(test_client, "ih_list")
    h = _auth(user["token"], user["workspaceId"])
    p = await _create_project(test_client, user, "L")
    await _set_health(test_client, user, p["id"], "on_track")
    await test_client.post(
        "/api/initiatives",
        headers=h,
        json={"name": "列表健", "projectIds": [p["id"]]},
    )
    listed = await test_client.get("/api/initiatives", headers=h)
    assert listed.status_code == 200
    rows = listed.json()["data"]["rows"]
    hit = next(r for r in rows if r["name"] == "列表健")
    assert hit["healthSummary"]["overall"] == "on_track"
    assert hit["healthSummary"]["projectCount"] == 1
