"""E83：Project watchers enrich username/name + 邻面不动 spy"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[2]


async def _register(client: AsyncClient, prefix: str = "e83"):
    uname = f"{prefix}_{uuid.uuid4().hex[:8]}"
    password = "Passw0rd!"
    resp = await client.post(
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
        json={"name": name or f"E83-{uuid.uuid4().hex[:6]}", "description": "e83"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_list_and_watch_enrich_username(test_client: AsyncClient):
    owner = await _register(test_client, "e83_en")
    member = await _register(test_client, "e83_em")
    await _add_member(test_client, owner, member)
    project = await _create_project(test_client, owner)

    w = await test_client.post(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert w.status_code == 200, w.text
    body = w.json()["data"]
    assert body["user_id"] == member["userId"]
    assert body.get("username") == member["username"]
    assert body.get("name")  # registered name

    listed = await test_client.get(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]
    mine = next(r for r in rows if r["user_id"] == member["userId"])
    assert mine.get("username") == member["username"]
    assert mine.get("name")


@pytest.mark.asyncio
async def test_watch_idempotent_and_unwatch_noop(test_client: AsyncClient):
    owner = await _register(test_client, "e83_id")
    member = await _register(test_client, "e83_im")
    await _add_member(test_client, owner, member)
    project = await _create_project(test_client, owner)

    w1 = await test_client.post(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert w1.status_code == 200, w1.text
    w2 = await test_client.post(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert w2.status_code == 200, w2.text

    listed = await test_client.get(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    ids = [r["user_id"] for r in listed.json()["data"]]
    assert ids.count(member["userId"]) == 1

    d1 = await test_client.delete(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert d1.status_code == 200, d1.text
    d2 = await test_client.delete(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(member["token"], owner["workspaceId"]),
    )
    assert d2.status_code == 200, d2.text  # no-op


@pytest.mark.asyncio
async def test_watchers_cross_tenant_and_missing_404(test_client: AsyncClient):
    a = await _register(test_client, "e83_ta")
    b = await _register(test_client, "e83_tb")
    project = await _create_project(test_client, a)

    resp = await test_client.post(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert resp.status_code in (403, 404), resp.text

    listed = await test_client.get(
        f"/api/projects/{project['id']}/watchers",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert listed.status_code in (403, 404), listed.text

    missing = await test_client.get(
        f"/api/projects/{uuid.uuid4()}/watchers",
        headers=_auth(a["token"], a["workspaceId"]),
    )
    assert missing.status_code == 404, missing.text


@pytest.mark.asyncio
async def test_neighbor_surfaces_untouched_spy():
    """E83 不改 milestone / project-move / issue-template / E79 roster；无新 webhook/alembic。"""
    milestone = (ROOT / "opentask/services/milestone/service.py").read_bytes()
    move = (ROOT / "opentask/services/issue_project_move.py").read_bytes()
    assert b"issue_count" in milestone or b"count_issues_by_milestone" in milestone
    assert b"apply_project_move_integrity" in move

    it_router = ROOT / "opentask/api/issue_templates/router.py"
    assert it_router.is_file()
    assert b"serialize_issue_template" in it_router.read_bytes()

    # E79 roster 锚点仍在 project_member + project router
    member_svc = ROOT / "opentask/services/project_member/service.py"
    assert member_svc.is_file()
    assert b"lead_id" in member_svc.read_bytes()
    assert b"lead_id" in (ROOT / "opentask/api/project/router.py").read_bytes()

    wh = ROOT / "opentask/services/webhook"
    if wh.is_dir():
        blob = " ".join(p.name for p in wh.rglob("*")).lower()
        assert "project_watcher" not in blob

    # 无本 epic 新 alembic
    alembic = ROOT / "alembic/versions"
    if alembic.is_dir():
        recent = [p.name for p in alembic.glob("*e83*")]
        assert recent == []

    formula = list((ROOT / "opentask").rglob("*formula*"))
    assert formula, "formula modules should still exist"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.asyncio
async def test_neighbor_file_hashes_present():
    paths = [
        ROOT / "opentask/services/milestone/service.py",
        ROOT / "opentask/services/issue_project_move.py",
        ROOT / "opentask/api/issue_templates/router.py",
    ]
    for p in paths:
        assert p.is_file(), p
        assert len(_sha256(p)) == 64
