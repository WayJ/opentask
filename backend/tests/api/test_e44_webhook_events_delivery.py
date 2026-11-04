"""E44：Webhook event pack + delivery reliability v1."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from opentask.models.workspace_webhook.model import WEBHOOK_EVENTS


async def _register(client: AsyncClient, prefix: str = "e44"):
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


class _FakeResp:
    def __init__(self, status_code: int = 200, text: str = "ok"):
        self.status_code = status_code
        self.text = text


def test_webhook_events_include_e44_pack():
    assert "issue.assignee_changed" in WEBHOOK_EVENTS
    assert "issue.label_added" in WEBHOOK_EVENTS
    assert "issue.label_removed" in WEBHOOK_EVENTS


@pytest.mark.asyncio
async def test_create_webhook_accepts_new_events(test_client: AsyncClient):
    user = await _register(test_client, "e44_ev")
    h = _auth(user["token"], user["workspaceId"])
    resp = await test_client.post(
        "/api/webhooks",
        headers=h,
        json={
            "url": "https://example.com/e44",
            "events": [
                "issue.assignee_changed",
                "issue.label_added",
                "issue.label_removed",
            ],
        },
    )
    assert resp.status_code == 200, resp.text
    events = resp.json()["data"]["events"]
    assert "issue.assignee_changed" in events
    assert "issue.label_added" in events
    assert "issue.label_removed" in events


@pytest.mark.asyncio
async def test_assignee_change_fires_dedicated_and_updated(test_client: AsyncClient):
    owner = await _register(test_client, "e44_asg")
    other = await _register(test_client, "e44_asg2")
    await _add_member(test_client, owner, other, role="member")
    h = _auth(owner["token"], owner["workspaceId"])

    issue = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "assignee-wh",
            "type": "feature",
            "status": "open",
            "priority": "medium",
        },
    )
    assert issue.status_code == 200, issue.text
    issue_id = issue.json()["data"]["id"]

    with patch(
        "opentask.services.workspace_webhook.service.WorkspaceWebhookService.dispatch_event",
        new_callable=AsyncMock,
    ) as dispatch:
        # subscribe via real webhook row so validation passes — but spy dispatch
        await test_client.post(
            "/api/webhooks",
            headers=h,
            json={
                "url": "https://example.com/asg",
                "events": ["issue.updated", "issue.assignee_changed"],
            },
        )
        patched = await test_client.put(
            f"/api/issues/{issue_id}",
            headers=h,
            json={"assignee_id": other["userId"]},
        )
        assert patched.status_code == 200, patched.text

        types = [c.kwargs.get("event_type") for c in dispatch.await_args_list]
        assert "issue.updated" in types
        assert "issue.assignee_changed" in types
        asg_calls = [
            c
            for c in dispatch.await_args_list
            if c.kwargs.get("event_type") == "issue.assignee_changed"
        ]
        assert asg_calls
        data = asg_calls[0].kwargs.get("data") or {}
        assert data.get("to") == other["userId"]
        assert data.get("from") is None or data.get("from") == ""
        assert data.get("actorUserId") == owner["userId"]
        assert data.get("id") == issue_id


@pytest.mark.asyncio
async def test_label_add_remove_fire_dedicated_only(test_client: AsyncClient):
    user = await _register(test_client, "e44_lbl")
    h = _auth(user["token"], user["workspaceId"])

    issue = await test_client.post(
        "/api/issues",
        headers=h,
        json={
            "title": "label-wh",
            "type": "feature",
            "status": "open",
            "priority": "medium",
        },
    )
    assert issue.status_code == 200, issue.text
    issue_id = issue.json()["data"]["id"]

    tag = await test_client.post(
        "/api/tags",
        headers=h,
        json={"name": f"e44-{uuid.uuid4().hex[:6]}", "color": "#336699"},
    )
    assert tag.status_code == 200, tag.text
    tag_id = tag.json()["data"]["id"]

    await test_client.post(
        "/api/webhooks",
        headers=h,
        json={
            "url": "https://example.com/lbl",
            "events": ["issue.label_added", "issue.label_removed", "issue.updated"],
        },
    )

    with patch(
        "opentask.services.workspace_webhook.service.WorkspaceWebhookService.dispatch_event",
        new_callable=AsyncMock,
    ) as dispatch:
        add = await test_client.post(
            f"/api/issues/{issue_id}/tags/{tag_id}",
            headers=h,
        )
        assert add.status_code == 200, add.text
        types_add = [c.kwargs.get("event_type") for c in dispatch.await_args_list]
        assert "issue.label_added" in types_add
        assert "issue.updated" not in types_add
        added = next(
            c
            for c in dispatch.await_args_list
            if c.kwargs.get("event_type") == "issue.label_added"
        )
        assert added.kwargs["data"]["labelId"] == tag_id
        assert added.kwargs["data"]["id"] == issue_id

        dispatch.reset_mock()
        rem = await test_client.delete(
            f"/api/issues/{issue_id}/tags/{tag_id}",
            headers=h,
        )
        assert rem.status_code == 200, rem.text
        types_rem = [c.kwargs.get("event_type") for c in dispatch.await_args_list]
        assert "issue.label_removed" in types_rem
        assert "issue.updated" not in types_rem
