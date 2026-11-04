"""E11-S3: webhook applies Issue status only when WS hooks enabled."""
from __future__ import annotations

import json
import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "hook"):
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
    headers = {"Authorization": f"Bearer {token}"}
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    return headers


async def _create_issue(client: AsyncClient, user: dict, title: str = "Hook Feature") -> dict:
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": title,
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "reporter_id": user["userId"],
        },
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _enable_hooks(client: AsyncClient, user: dict, enabled: bool = True):
    resp = await client.patch(
        f"/api/workspaces/{user['workspaceId']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"gitStatusHooksEnabled": enabled},
    )
    assert resp.status_code == 200, resp.text


async def _get_issue(client: AsyncClient, user: dict, issue_id: str) -> dict:
    resp = await client.get(
        f"/api/issues/{issue_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _pr_payload(*, head: str, number: int, state: str = "open", merged: bool = False, draft: bool = False):
    return {
        "action": "opened" if not merged else "closed",
        "pull_request": {
            "html_url": f"https://github.com/acme/app/pull/{number}",
            "number": number,
            "state": state,
            "merged": merged,
            "draft": draft,
            "title": "Hook PR",
            "head": {"ref": head},
        },
    }


@pytest.mark.asyncio
async def test_hooks_off_pr_open_no_status_change(test_client: AsyncClient, monkeypatch):
    monkeypatch.delenv("WEBHOOK_GITHUB_SECRET", raising=False)
    user = await _register(test_client, "hoff")
    issue = await _create_issue(test_client, user)
    head = f"{issue['issue_code']}-hook-feature"
    resp = await test_client.post(
        "/api/webhooks/github/pull-request",
        content=json.dumps(_pr_payload(head=head, number=501)),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    got = await _get_issue(test_client, user, issue["id"])
    assert got["status"] == "open"


@pytest.mark.asyncio
async def test_hooks_on_pr_open_moves_open_to_in_progress(test_client: AsyncClient, monkeypatch):
    monkeypatch.delenv("WEBHOOK_GITHUB_SECRET", raising=False)
    user = await _register(test_client, "hon")
    await _enable_hooks(test_client, user, True)
    issue = await _create_issue(test_client, user)
    head = f"{issue['issue_code']}-hook-feature"
    resp = await test_client.post(
        "/api/webhooks/github/pull-request",
        content=json.dumps(_pr_payload(head=head, number=502)),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"].get("issueStatus") == "in_progress"
    got = await _get_issue(test_client, user, issue["id"])
    assert got["status"] == "in_progress"


@pytest.mark.asyncio
async def test_hooks_on_merged_sets_resolved(test_client: AsyncClient, monkeypatch):
    monkeypatch.delenv("WEBHOOK_GITHUB_SECRET", raising=False)
    user = await _register(test_client, "hmrg")
    await _enable_hooks(test_client, user, True)
    issue = await _create_issue(test_client, user)
    head = f"{issue['issue_code']}-hook-feature"
    # first open → in_progress
    await test_client.post(
        "/api/webhooks/github/pull-request",
        content=json.dumps(_pr_payload(head=head, number=503)),
        headers={"Content-Type": "application/json"},
    )
    resp = await test_client.post(
        "/api/webhooks/github/pull-request",
        content=json.dumps(
            _pr_payload(head=head, number=503, state="closed", merged=True)
        ),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"].get("issueStatus") == "resolved"
    got = await _get_issue(test_client, user, issue["id"])
    assert got["status"] == "resolved"


@pytest.mark.asyncio
async def test_hooks_on_open_does_not_disturb_in_progress(test_client: AsyncClient, monkeypatch):
    monkeypatch.delenv("WEBHOOK_GITHUB_SECRET", raising=False)
    user = await _register(test_client, "hip")
    h = _auth(user["token"], user["workspaceId"])
    await _enable_hooks(test_client, user, True)
    issue = await _create_issue(test_client, user)
    # move to in_progress manually
    patched = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"status": "in_progress"},
    )
    assert patched.status_code == 200, patched.text
    head = f"{issue['issue_code']}-hook-feature"
    resp = await test_client.post(
        "/api/webhooks/github/pull-request",
        content=json.dumps(_pr_payload(head=head, number=504)),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    assert "issueStatus" not in resp.json()["data"] or resp.json()["data"].get("issueStatus") in (
        None,
        "in_progress",
    )
    got = await _get_issue(test_client, user, issue["id"])
    assert got["status"] == "in_progress"


@pytest.mark.asyncio
async def test_hooks_on_closed_unmerged_no_change(test_client: AsyncClient, monkeypatch):
    monkeypatch.delenv("WEBHOOK_GITHUB_SECRET", raising=False)
    user = await _register(test_client, "hcl")
    await _enable_hooks(test_client, user, True)
    issue = await _create_issue(test_client, user)
    head = f"{issue['issue_code']}-hook-feature"
    resp = await test_client.post(
        "/api/webhooks/github/pull-request",
        content=json.dumps(
            _pr_payload(head=head, number=505, state="closed", merged=False)
        ),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    got = await _get_issue(test_client, user, issue["id"])
    assert got["status"] == "open"
