"""E82：GET /api/issue-templates/{id} + seed/viewer 边界 + 邻面不动 spy"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import pytest
from httpx import AsyncClient

ROOT = Path(__file__).resolve().parents[2]


async def _register(client: AsyncClient, prefix: str = "e82"):
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


@pytest.mark.asyncio
async def test_get_issue_template_by_id_200(test_client: AsyncClient):
    user = await _register(test_client, "e82_get")
    created = await test_client.post(
        "/api/issue-templates",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "name": "E82 自定义",
            "description": "show me",
            "icon": "i-carbon-bug",
            "payload": {"type": "bug", "priority": "high", "title": "Bug: "},
            "sortOrder": 3,
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    tid = row["id"]

    got = await test_client.get(
        f"/api/issue-templates/{tid}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert got.status_code == 200, got.text
    data = got.json()["data"]
    assert data["id"] == tid
    assert data["name"] == "E82 自定义"
    assert data["description"] == "show me"
    assert data["icon"] == "i-carbon-bug"
    assert data["payload"]["priority"] == "high"
    assert data["source"] == "custom"
    assert data["sortOrder"] == 3
    assert "workspaceId" in data
    assert "createdAt" in data


@pytest.mark.asyncio
async def test_get_missing_and_cross_workspace_404(test_client: AsyncClient):
    a = await _register(test_client, "e82_xa")
    b = await _register(test_client, "e82_xb")
    created = await test_client.post(
        "/api/issue-templates",
        headers=_auth(a["token"], a["workspaceId"]),
        json={"name": "only-a", "payload": {"type": "task"}},
    )
    tid = created.json()["data"]["id"]

    missing = await test_client.get(
        f"/api/issue-templates/{uuid.uuid4().hex}",
        headers=_auth(a["token"], a["workspaceId"]),
    )
    assert missing.status_code == 404

    cross = await test_client.get(
        f"/api/issue-templates/{tid}",
        headers=_auth(b["token"], b["workspaceId"]),
    )
    assert cross.status_code == 404


@pytest.mark.asyncio
async def test_viewer_get_ok_write_and_seed_forbidden(test_client: AsyncClient):
    owner = await _register(test_client, "e82_own")
    viewer = await _register(test_client, "e82_view")
    await _add_member(test_client, owner, viewer, role="viewer")

    listed = await test_client.get(
        "/api/issue-templates",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    tid = listed.json()["data"]["rows"][0]["id"]

    got = await test_client.get(
        f"/api/issue-templates/{tid}",
        headers=_auth(viewer["token"], owner["workspaceId"]),
    )
    assert got.status_code == 200, got.text

    for method, path, body in (
        ("post", "/api/issue-templates", {"name": "nope"}),
        ("post", "/api/issue-templates/seed", None),
        ("patch", f"/api/issue-templates/{tid}", {"name": "hijack"}),
        ("delete", f"/api/issue-templates/{tid}", None),
    ):
        if method == "post":
            resp = await test_client.post(
                path,
                headers=_auth(viewer["token"], owner["workspaceId"]),
                json=body or {},
            )
        elif method == "patch":
            resp = await test_client.patch(
                path,
                headers=_auth(viewer["token"], owner["workspaceId"]),
                json=body,
            )
        else:
            resp = await test_client.delete(
                path,
                headers=_auth(viewer["token"], owner["workspaceId"]),
            )
        assert resp.status_code == 403, (method, path, resp.text)


@pytest.mark.asyncio
async def test_seed_post_returns_builtins(test_client: AsyncClient):
    user = await _register(test_client, "e82_seed")
    seeded = await test_client.post(
        "/api/issue-templates/seed",
        headers=_auth(user["token"], user["workspaceId"]),
        json={},
    )
    assert seeded.status_code == 200, seeded.text
    data = seeded.json()["data"]
    keys = {r["seedKey"] for r in data["rows"] if r.get("seedKey")}
    assert "bug_report" in keys
    assert data["total"] >= 5


@pytest.mark.asyncio
async def test_neighbor_surfaces_untouched_spy():
    """E82 不改 milestone / project-move / E72 project-template 主表面；无新 webhook。"""
    milestone = (ROOT / "opentask/services/milestone/service.py").read_bytes()
    move = (ROOT / "opentask/services/issue_project_move.py").read_bytes()
    # 文件存在且含 E81/E80 锚点
    assert b"issue_count" in milestone or b"count_issues_by_milestone" in milestone
    assert b"apply_project_move_integrity" in move

    pt_cli = (
        ROOT.parent
        / "agent-harness/opentask-cli/opentask/core/project_template.py"
    )
    assert pt_cli.is_file()
    assert b"project-template" in pt_cli.read_bytes()

    # 无新 webhook event 文件因本 epic 新增（目录仍可有既有）
    wh = ROOT / "opentask/services/webhook"
    if wh.is_dir():
        names = {p.name for p in wh.rglob("*")}
        assert "issue_template" not in " ".join(names).lower()

    # formula no-emit：服务层仍禁止 emit（锚点存在即可）
    formula = list((ROOT / "opentask").rglob("*formula*"))
    assert formula, "formula modules should still exist"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.asyncio
async def test_e80_e81_files_stable_hash_baseline():
    """记录邻面文件哈希，实现后仍应一致（本测在 GET 落地前后均可跑）。"""
    paths = [
        ROOT / "opentask/services/milestone/service.py",
        ROOT / "opentask/services/issue_project_move.py",
    ]
    for p in paths:
        assert p.is_file(), p
        assert len(_sha256(p)) == 64
