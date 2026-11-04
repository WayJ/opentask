"""E29：Outbound Webhooks CRUD + 投递签名 + 权限/租户."""
from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient, Response


async def _register(client: AsyncClient, prefix: str = "wh"):
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


@pytest.mark.asyncio
async def test_webhook_crud_secret_once_and_test(test_client: AsyncClient):
    user = await _register(test_client, "wh_crud")
    h = _auth(user["token"], user["workspaceId"])

    with patch(
        "opentask.services.workspace_webhook.service.httpx.AsyncClient"
    ) as client_cls:
        inst = AsyncMock()
        inst.__aenter__.return_value = inst
        inst.__aexit__.return_value = None
        inst.post = AsyncMock(return_value=_FakeResp(200, "ok"))
        client_cls.return_value = inst

        created = await test_client.post(
            "/api/webhooks",
            headers=h,
            json={
                "url": "https://example.com/hook",
                "events": ["issue.created", "issue.updated"],
                "name": "Demo",
            },
        )
        assert created.status_code == 200, created.text
        row = created.json()["data"]
        assert row["url"] == "https://example.com/hook"
        assert "secret" in row and len(row["secret"]) >= 16
        assert row["secretHint"].endswith(row["secret"][-4:])
        wid = row["id"]
        secret = row["secret"]

        listed = await test_client.get("/api/webhooks", headers=h)
        assert listed.status_code == 200, listed.text
        listed_row = next(r for r in listed.json()["data"]["rows"] if r["id"] == wid)
        assert "secret" not in listed_row
        assert listed_row["secretHint"].endswith(secret[-4:])

        got = await test_client.get(f"/api/webhooks/{wid}", headers=h)
        assert got.status_code == 200, got.text
        assert "secret" not in got.json()["data"]

        patched = await test_client.patch(
            f"/api/webhooks/{wid}",
            headers=h,
            json={"enabled": False, "events": ["comment.created"]},
        )
        assert patched.status_code == 200, patched.text
        assert patched.json()["data"]["enabled"] is False
        assert patched.json()["data"]["events"] == ["comment.created"]

        # re-enable for test
        await test_client.patch(
            f"/api/webhooks/{wid}", headers=h, json={"enabled": True}
        )

        tested = await test_client.post(f"/api/webhooks/{wid}/test", headers=h)
        assert tested.status_code == 200, tested.text
        assert tested.json()["data"]["success"] is True
        assert inst.post.await_count >= 1
        # verify signature header on last call
        call_kwargs = inst.post.await_args
        sent_headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
        body = call_kwargs.kwargs.get("content") or call_kwargs[1].get("content")
        assert sent_headers["X-OpenTask-Event"] == "webhook.test"
        expected = "sha256=" + hmac.new(
            secret.encode("utf-8"), body, hashlib.sha256
        ).hexdigest()
        assert sent_headers["X-OpenTask-Signature"] == expected
        payload = json.loads(body.decode("utf-8"))
        assert payload["type"] == "webhook.test"
        assert payload["workspaceId"] == user["workspaceId"]

        detail = await test_client.get(f"/api/webhooks/{wid}", headers=h)
        deliveries = detail.json()["data"].get("deliveries") or []
        assert any(d["eventType"] == "webhook.test" and d["success"] for d in deliveries)

        deleted = await test_client.delete(f"/api/webhooks/{wid}", headers=h)
        assert deleted.status_code == 200, deleted.text
        missing = await test_client.get(f"/api/webhooks/{wid}", headers=h)
        assert missing.status_code == 404


@pytest.mark.asyncio
async def test_webhook_permissions_and_cross_tenant(test_client: AsyncClient):
    owner = await _register(test_client, "wh_own")
    member = await _register(test_client, "wh_mem")
    viewer = await _register(test_client, "wh_view")
    other = await _register(test_client, "wh_oth")
    await _add_member(test_client, owner, member, role="member")
    await _add_member(test_client, owner, viewer, role="viewer")

    h_owner = _auth(owner["token"], owner["workspaceId"])
    with patch(
        "opentask.services.workspace_webhook.service.httpx.AsyncClient"
    ) as client_cls:
        inst = AsyncMock()
        inst.__aenter__.return_value = inst
        inst.__aexit__.return_value = None
        inst.post = AsyncMock(return_value=_FakeResp(200))
        client_cls.return_value = inst

        created = await test_client.post(
            "/api/webhooks",
            headers=h_owner,
            json={"url": "https://example.com/a", "events": ["issue.created"]},
        )
        assert created.status_code == 200, created.text
        wid = created.json()["data"]["id"]

    h_member = _auth(member["token"], owner["workspaceId"])
    listed = await test_client.get("/api/webhooks", headers=h_member)
    assert listed.status_code == 200, listed.text

    forbidden_member_write = await test_client.post(
        "/api/webhooks",
        headers=h_member,
        json={"url": "https://example.com/b", "events": ["issue.created"]},
    )
    assert forbidden_member_write.status_code == 403

    h_viewer = _auth(viewer["token"], owner["workspaceId"])
    viewer_list = await test_client.get("/api/webhooks", headers=h_viewer)
    assert viewer_list.status_code == 403

    # cross tenant: other owner cannot see
    h_other = _auth(other["token"], other["workspaceId"])
    cross = await test_client.get(f"/api/webhooks/{wid}", headers=h_other)
    assert cross.status_code == 404

    # other tries with owner's workspace header but not a member
    h_intruder = _auth(other["token"], owner["workspaceId"])
    denied = await test_client.get("/api/webhooks", headers=h_intruder)
    assert denied.status_code in (403, 404)


@pytest.mark.asyncio
async def test_webhook_fires_on_issue_created(test_client: AsyncClient):
    user = await _register(test_client, "wh_fire")
    h = _auth(user["token"], user["workspaceId"])

    with patch(
        "opentask.services.workspace_webhook.service.httpx.AsyncClient"
    ) as client_cls:
        inst = AsyncMock()
        inst.__aenter__.return_value = inst
        inst.__aexit__.return_value = None
        inst.post = AsyncMock(return_value=_FakeResp(200))
        client_cls.return_value = inst

        created = await test_client.post(
            "/api/webhooks",
            headers=h,
            json={
                "url": "https://hooks.example/opentask",
                "events": ["issue.created"],
            },
        )
        assert created.status_code == 200, created.text
        secret = created.json()["data"]["secret"]
        wid = created.json()["data"]["id"]

        issue = await test_client.post(
            "/api/issues",
            headers=h,
            json={
                "title": "fire-me",
                "type": "feature",
                "status": "open",
                "priority": "medium",
            },
        )
        assert issue.status_code == 200, issue.text

        # find issue.created delivery call
        assert inst.post.await_count >= 1
        found = False
        for call in inst.post.await_args_list:
            headers = call.kwargs.get("headers") or {}
            body = call.kwargs.get("content") or b""
            if headers.get("X-OpenTask-Event") == "issue.created":
                expected = "sha256=" + hmac.new(
                    secret.encode("utf-8"), body, hashlib.sha256
                ).hexdigest()
                assert headers["X-OpenTask-Signature"] == expected
                payload = json.loads(body.decode("utf-8"))
                assert payload["data"]["title"] == "fire-me"
                found = True
                break
        assert found, "issue.created webhook not delivered"

        detail = await test_client.get(f"/api/webhooks/{wid}", headers=h)
        deliveries = detail.json()["data"].get("deliveries") or []
        assert any(d["eventType"] == "issue.created" and d["success"] for d in deliveries)


@pytest.mark.asyncio
async def test_webhook_retry_on_failure(test_client: AsyncClient):
    user = await _register(test_client, "wh_retry")
    h = _auth(user["token"], user["workspaceId"])

    with patch(
        "opentask.services.workspace_webhook.service.httpx.AsyncClient"
    ) as client_cls, patch(
        "opentask.services.workspace_webhook.service.asyncio.sleep",
        new_callable=AsyncMock,
    ) as sleep_mock:
        inst = AsyncMock()
        inst.__aenter__.return_value = inst
        inst.__aexit__.return_value = None
        inst.post = AsyncMock(side_effect=[_FakeResp(500, "nope"), _FakeResp(200, "ok")])
        client_cls.return_value = inst

        created = await test_client.post(
            "/api/webhooks",
            headers=h,
            json={"url": "https://example.com/retry", "events": ["issue.created"]},
        )
        assert created.status_code == 200, created.text
        wid = created.json()["data"]["id"]

        tested = await test_client.post(f"/api/webhooks/{wid}/test", headers=h)
        assert tested.status_code == 200, tested.text
        assert tested.json()["data"]["success"] is True
        assert inst.post.await_count == 2
        sleep_mock.assert_awaited()
