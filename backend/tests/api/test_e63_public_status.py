"""E63：Customer Request public status portal — token lifecycle, public card, replies."""
from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

# Disable public request rate limit by default; dedicated test re-enables.
os.environ["OPENTASK_PUBLIC_REQUEST_RATE_LIMIT"] = "0"


async def _register(client: AsyncClient, prefix: str = "e63"):
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


async def _create_customer_and_request(client: AsyncClient, user: dict, *, title: str = "Need SSO"):
    h = _auth(user["token"], user["workspaceId"])
    cust = await client.post("/api/customers", headers=h, json={"name": f"Cust-{uuid.uuid4().hex[:6]}"})
    assert cust.status_code == 200, cust.text
    cid = cust.json()["data"]["id"]
    req = await client.post(
        "/api/customer-requests",
        headers=h,
        json={"customerId": cid, "title": title, "body": "internal only", "priority": "high"},
    )
    assert req.status_code == 200, req.text
    return req.json()["data"], h


async def _create_issue(client: AsyncClient, user: dict, title: str = "linked") -> dict:
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"title": title, "type": "feature", "status": "open", "priority": "medium"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_e63_enable_rotate_revoke_token_lifecycle(test_client: AsyncClient):
    user = await _register(test_client, "e63_life")
    row, h = await _create_customer_and_request(test_client, user)
    rid = row["id"]

    # Default: no status link
    detail = await test_client.get(f"/api/customer-requests/{rid}", headers=h)
    assert detail.status_code == 200, detail.text
    sl = detail.json()["data"].get("statusLink") or {}
    assert sl.get("enabled") is False
    assert not sl.get("url")
    assert "token" not in detail.json()["data"]

    enabled = await test_client.post(
        f"/api/customer-requests/{rid}/status-link/enable",
        headers=h,
        json={"publicRepliesEnabled": True},
    )
    assert enabled.status_code == 200, enabled.text
    edata = enabled.json()["data"]
    assert edata["statusLink"]["enabled"] is True
    assert edata["statusLink"]["publicRepliesEnabled"] is True
    assert edata["statusLink"]["url"].startswith("/r/")
    token1 = edata["token"]
    assert token1
    assert edata["statusLink"]["url"] == f"/r/{token1}"

    rotated = await test_client.post(
        f"/api/customer-requests/{rid}/status-link/rotate",
        headers=h,
    )
    assert rotated.status_code == 200, rotated.text
    token2 = rotated.json()["data"]["token"]
    assert token2 and token2 != token1

    revoked = await test_client.post(
        f"/api/customer-requests/{rid}/status-link/revoke",
        headers=h,
    )
    assert revoked.status_code == 200, revoked.text
    rdata = revoked.json()["data"]
    assert rdata["statusLink"]["enabled"] is False
    assert not rdata["statusLink"].get("url")
    assert "token" not in rdata or rdata.get("token") in (None, "")


@pytest.mark.asyncio
async def test_e63_viewer_cannot_enable_cross_tenant_404(test_client: AsyncClient):
    owner = await _register(test_client, "e63_own")
    viewer = await _register(test_client, "e63_view")
    other = await _register(test_client, "e63_oth")
    await _add_member(test_client, owner, viewer, role="viewer")
    row, oh = await _create_customer_and_request(test_client, owner)
    rid = row["id"]

    vh = _auth(viewer["token"], owner["workspaceId"])
    forbidden = await test_client.post(
        f"/api/customer-requests/{rid}/status-link/enable",
        headers=vh,
    )
    assert forbidden.status_code == 403, forbidden.text

    xh = _auth(other["token"], other["workspaceId"])
    missing = await test_client.post(
        f"/api/customer-requests/{rid}/status-link/enable",
        headers=xh,
    )
    assert missing.status_code == 404, missing.text


@pytest.mark.asyncio
async def test_e63_public_get_redacted_card(test_client: AsyncClient):
    user = await _register(test_client, "e63_pub")
    row, h = await _create_customer_and_request(test_client, user, title="Portal Card")
    rid = row["id"]
    issue = await _create_issue(test_client, user, title="linked-issue")
    link = await test_client.post(
        f"/api/customer-requests/{rid}/issues",
        headers=h,
        json={"issueId": issue["id"]},
    )
    assert link.status_code == 200, link.text

    enabled = await test_client.post(
        f"/api/customer-requests/{rid}/status-link/enable",
        headers=h,
    )
    assert enabled.status_code == 200, enabled.text
    token = enabled.json()["data"]["token"]

    pub = await test_client.get(f"/api/public/customer-requests/{token}")
    assert pub.status_code == 200, pub.text
    card = pub.json()["data"]
    assert card["title"] == "Portal Card"
    assert card["status"] == "open"
    assert card["priority"] == "high"
    assert card["customerName"]
    assert card["linkedIssueCount"] == 1
    code = issue.get("issueCode") or issue.get("issue_code")
    assert code
    assert card["linkedIssueCodes"] == [code]
    assert card["publicRepliesEnabled"] is False
    assert "workspaceId" not in card
    assert "body" not in card
    assert "token" not in card
    assert "id" not in card
    assert "createdBy" not in card
    # no issue description / internal fields
    assert "issues" not in card
    assert "issueIds" not in card


@pytest.mark.asyncio
async def test_e63_public_get_404_revoked_and_unknown(test_client: AsyncClient):
    user = await _register(test_client, "e63_404")
    row, h = await _create_customer_and_request(test_client, user)
    rid = row["id"]
    enabled = await test_client.post(
        f"/api/customer-requests/{rid}/status-link/enable", headers=h
    )
    token = enabled.json()["data"]["token"]
    await test_client.post(f"/api/customer-requests/{rid}/status-link/revoke", headers=h)

    assert (await test_client.get(f"/api/public/customer-requests/{token}")).status_code == 404
    assert (await test_client.get("/api/public/customer-requests/not-a-real-token")).status_code == 404

    # rotate invalidates old
    enabled2 = await test_client.post(
        f"/api/customer-requests/{rid}/status-link/enable", headers=h
    )
    t1 = enabled2.json()["data"]["token"]
    rotated = await test_client.post(
        f"/api/customer-requests/{rid}/status-link/rotate", headers=h
    )
    t2 = rotated.json()["data"]["token"]
    assert (await test_client.get(f"/api/public/customer-requests/{t1}")).status_code == 404
    assert (await test_client.get(f"/api/public/customer-requests/{t2}")).status_code == 200


@pytest.mark.asyncio
async def test_e63_public_replies_with_and_without_issue(test_client: AsyncClient):
    user = await _register(test_client, "e63_rep")
    row, h = await _create_customer_and_request(test_client, user, title="Reply Path")
    rid = row["id"]

    # No issue → public_replies table
    en = await test_client.post(
        f"/api/customer-requests/{rid}/status-link/enable",
        headers=h,
        json={"publicRepliesEnabled": True},
    )
    token = en.json()["data"]["token"]

    # disabled replies → 404
    await test_client.patch(
        f"/api/customer-requests/{rid}",
        headers=h,
        json={"publicRepliesEnabled": False},
    )
    denied = await test_client.post(
        f"/api/public/customer-requests/{token}/replies",
        json={"body": "hello"},
    )
    assert denied.status_code == 404, denied.text

    await test_client.patch(
        f"/api/customer-requests/{rid}",
        headers=h,
        json={"publicRepliesEnabled": True},
    )

    with patch(
        "opentask.services.customer.service.fire_webhooks",
        new_callable=AsyncMock,
    ) as fw:
        posted = await test_client.post(
            f"/api/public/customer-requests/{token}/replies",
            json={"body": "customer note without issue"},
        )
        assert posted.status_code == 200, posted.text
        fw.assert_not_called()

    detail = await test_client.get(f"/api/customer-requests/{rid}", headers=h)
    assert detail.status_code == 200
    replies = detail.json()["data"].get("publicReplies") or []
    assert any(r.get("body") == "customer note without issue" for r in replies)

    pub = await test_client.get(f"/api/public/customer-requests/{token}")
    recent = pub.json()["data"].get("recentPublicReplies") or []
    assert any(r.get("body") == "customer note without issue" for r in recent)

    # With linked issue → IssueComment + comment.created webhook, no inbox notify
    issue = await _create_issue(test_client, user, title="for-comment")
    await test_client.post(
        f"/api/customer-requests/{rid}/issues",
        headers=h,
        json={"issueId": issue["id"]},
    )

    with (
        patch(
            "opentask.services.customer.service.fire_webhooks",
            new_callable=AsyncMock,
        ) as fw,
        patch(
            "opentask.services.notification.service.NotificationService.notify_comment",
            new_callable=AsyncMock,
        ) as notify,
    ):
        posted2 = await test_client.post(
            f"/api/public/customer-requests/{token}/replies",
            json={"body": "please ship SSO"},
        )
        assert posted2.status_code == 200, posted2.text
        assert fw.await_count >= 1
        event_types = [c.kwargs.get("event_type") or (c.args[1] if len(c.args) > 1 else None) for c in fw.await_args_list]
        # fire_webhooks(session, workspace_id=..., event_type=..., payload=...)
        called_types = []
        for c in fw.await_args_list:
            if c.kwargs.get("event_type"):
                called_types.append(c.kwargs["event_type"])
            elif len(c.args) >= 3:
                called_types.append(c.args[2] if False else c.kwargs.get("event_type"))
        # inspect more carefully
        flat = []
        for c in fw.await_args_list:
            flat.append(c.kwargs.copy())
            if c.args:
                flat[-1]["_args"] = c.args
        assert any(
            (c.kwargs.get("event_type") == "comment.created")
            or ("comment.created" in str(c))
            for c in fw.await_args_list
        ), flat
        notify.assert_not_called()

    comments = await test_client.get(
        f"/api/issues/{issue['id']}/comments",
        headers=h,
    )
    assert comments.status_code == 200, comments.text
    bodies = [
        (c.get("content") or c.get("body") or "")
        for c in (comments.json().get("data") or comments.json() or [])
        if isinstance(c, dict)
    ]
    # data may be list or {rows:[]}
    raw = comments.json().get("data")
    if isinstance(raw, dict):
        raw = raw.get("rows") or raw.get("comments") or []
    bodies = [(c.get("content") or c.get("body") or "") for c in (raw or [])]
    assert any("please ship SSO" in b for b in bodies), comments.text


@pytest.mark.asyncio
async def test_e63_public_get_no_webhook_no_emit(test_client: AsyncClient):
    user = await _register(test_client, "e63_spy")
    row, h = await _create_customer_and_request(test_client, user)
    en = await test_client.post(
        f"/api/customer-requests/{row['id']}/status-link/enable", headers=h
    )
    token = en.json()["data"]["token"]
    with patch(
        "opentask.services.customer.service.fire_webhooks",
        new_callable=AsyncMock,
    ) as fw:
        pub = await test_client.get(f"/api/public/customer-requests/{token}")
        assert pub.status_code == 200
        fw.assert_not_called()


@pytest.mark.asyncio
async def test_e63_public_rate_limit(test_client: AsyncClient, monkeypatch):
    from opentask.services.customer import service as cust_svc

    monkeypatch.setenv("OPENTASK_PUBLIC_REQUEST_RATE_LIMIT", "1")
    cust_svc.reset_public_rate_limit()
    # Force max=2 for fast test
    monkeypatch.setattr(cust_svc, "_RATE_MAX", 2)

    user = await _register(test_client, "e63_rl")
    row, h = await _create_customer_and_request(test_client, user)
    en = await test_client.post(
        f"/api/customer-requests/{row['id']}/status-link/enable", headers=h
    )
    token = en.json()["data"]["token"]

    assert (await test_client.get(f"/api/public/customer-requests/{token}")).status_code == 200
    assert (await test_client.get(f"/api/public/customer-requests/{token}")).status_code == 200
    third = await test_client.get(f"/api/public/customer-requests/{token}")
    assert third.status_code == 429, third.text

    monkeypatch.setenv("OPENTASK_PUBLIC_REQUEST_RATE_LIMIT", "0")
    cust_svc.reset_public_rate_limit()
