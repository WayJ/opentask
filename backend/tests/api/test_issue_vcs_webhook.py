"""E11-S2: PATCH PR links + GitHub webhook ingest (fixture; no live App)."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "wh"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str = "Fix Login") -> dict:
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


@pytest.mark.asyncio
async def test_patch_pr_link_status(test_client: AsyncClient):
    user = await _register(test_client, "pat")
    h = _auth(user["token"], user["workspaceId"])
    issue = await _create_issue(test_client, user)
    created = await test_client.post(
        f"/api/issues/{issue['id']}/vcs/links",
        headers=h,
        json={
            "kind": "pull_request",
            "prUrl": "https://github.com/org/repo/pull/9",
            "provider": "github",
            "status": "open",
            "externalId": "9",
        },
    )
    assert created.status_code == 200, created.text
    lid = created.json()["data"]["id"]

    patched = await test_client.patch(
        f"/api/issues/{issue['id']}/vcs/links/{lid}",
        headers=h,
        json={"status": "merged", "title": "Done"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["data"]["status"] == "merged"
    assert patched.json()["data"]["title"] == "Done"


@pytest.mark.asyncio
async def test_webhook_creates_link_from_head_ref(test_client: AsyncClient, monkeypatch):
    monkeypatch.delenv("WEBHOOK_GITHUB_SECRET", raising=False)
    user = await _register(test_client, "whc")
    issue = await _create_issue(test_client, user, title="Webhook Feature")
    code = issue["issue_code"]
    head = f"{code}-webhook-feature"
    payload = {
        "action": "opened",
        "pull_request": {
            "html_url": "https://github.com/acme/app/pull/42",
            "number": 42,
            "state": "open",
            "merged": False,
            "draft": False,
            "title": "Webhook Feature",
            "head": {"ref": head},
        },
        "repository": {"html_url": "https://github.com/acme/app"},
    }
    resp = await test_client.post(
        "/api/webhooks/github/pull-request",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["kind"] == "pull_request"
    assert data["issueId"] == issue["id"]
    assert data["status"] == "open"
    assert data["externalId"] == "42"
    assert data["branchName"] == head


@pytest.mark.asyncio
async def test_webhook_updates_existing_and_merged(test_client: AsyncClient, monkeypatch):
    monkeypatch.delenv("WEBHOOK_GITHUB_SECRET", raising=False)
    user = await _register(test_client, "whu")
    h = _auth(user["token"], user["workspaceId"])
    issue = await _create_issue(test_client, user)
    code = issue["issue_code"]
    url = "https://github.com/acme/app/pull/77"
    # seed via API
    await test_client.post(
        f"/api/issues/{issue['id']}/vcs/links",
        headers=h,
        json={
            "kind": "pull_request",
            "prUrl": url,
            "provider": "github",
            "status": "open",
            "externalId": "77",
            "branchName": f"{code}-x",
        },
    )
    payload = {
        "action": "closed",
        "pull_request": {
            "html_url": url,
            "number": 77,
            "state": "closed",
            "merged": True,
            "draft": False,
            "title": "Merged PR",
            "head": {"ref": f"{code}-x"},
        },
    }
    resp = await test_client.post(
        "/api/webhooks/github/pull-request",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "merged"
    assert resp.json()["data"]["title"] == "Merged PR"

    listed = await test_client.get(f"/api/issues/{issue['id']}/vcs/links", headers=h)
    prs = [r for r in listed.json()["data"]["rows"] if r["kind"] == "pull_request"]
    assert len(prs) == 1
    assert prs[0]["status"] == "merged"


@pytest.mark.asyncio
async def test_webhook_unmatched_404(test_client: AsyncClient, monkeypatch):
    monkeypatch.delenv("WEBHOOK_GITHUB_SECRET", raising=False)
    payload = {
        "action": "opened",
        "pull_request": {
            "html_url": "https://github.com/acme/app/pull/999",
            "number": 999,
            "state": "open",
            "merged": False,
            "title": "No match",
            "head": {"ref": "main"},
        },
    }
    resp = await test_client.post(
        "/api/webhooks/github/pull-request",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_webhook_bad_signature_401(test_client: AsyncClient, monkeypatch):
    monkeypatch.setenv("WEBHOOK_GITHUB_SECRET", "super-secret")
    payload = {"action": "opened", "pull_request": {"html_url": "https://x/1", "number": 1}}
    body = json.dumps(payload).encode()
    resp = await test_client.post(
        "/api/webhooks/github/pull-request",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=deadbeef",
        },
    )
    assert resp.status_code == 401, resp.text

    # valid signature still needs matchable issue — use empty after clearing? keep 401 path covered
    dig = hmac.new(b"super-secret", body, hashlib.sha256).hexdigest()
    resp2 = await test_client.post(
        "/api/webhooks/github/pull-request",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": f"sha256={dig}",
        },
    )
    # signature ok but incomplete / unmatched
    assert resp2.status_code in (400, 404), resp2.text
