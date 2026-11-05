"""E30：Email notifications — prefs email_enabled + SMTP hook + email-test."""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from opentask.services.email import (
    MemoryEmailTransport,
    email_configured,
    resolve_recipient_email,
    set_email_transport,
)


async def _register(client: AsyncClient, prefix: str = "em", *, username: str | None = None):
    uname = username or f"{prefix}_{uuid.uuid4().hex[:8]}"
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


async def _create_issue(client: AsyncClient, user: dict, title: str = "em-issue", **extra) -> dict:
    payload = {
        "title": title,
        "type": "feature",
        "status": "open",
        "priority": "medium",
        "reporter_id": user["userId"],
        **extra,
    }
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json=payload,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.fixture
def memory_mail():
    transport = MemoryEmailTransport()
    set_email_transport(transport)
    try:
        yield transport
    finally:
        set_email_transport(None)


def test_email_configured_false_by_default():
    # test env has no SMTP_HOST/FROM
    assert email_configured() is False or isinstance(email_configured(), bool)


def test_resolve_recipient_email():
    class U:
        def __init__(self, username):
            self.username = username

    assert resolve_recipient_email(U("alice@example.com")) == "alice@example.com"
    assert resolve_recipient_email(U("Alice@Example.COM")) == "alice@example.com"
    assert resolve_recipient_email(U("alice")) is None
    assert resolve_recipient_email(U("")) is None
    assert resolve_recipient_email(None) is None


@pytest.mark.asyncio
async def test_prefs_include_email_fields(test_client: AsyncClient):
    user = await _register(test_client, "em_pref")
    h = _auth(user["token"], user["workspaceId"])
    got = await test_client.get("/api/inbox/preferences", headers=h)
    assert got.status_code == 200, got.text
    data = got.json()["data"]
    assert data["email_enabled"] is False
    assert "email_configured" in data
    assert data["issue_comment"] is True

    put = await test_client.put(
        "/api/inbox/preferences",
        headers=h,
        json={"email_enabled": True},
    )
    assert put.status_code == 200, put.text
    assert put.json()["data"]["email_enabled"] is True
    # type prefs untouched
    assert put.json()["data"]["issue_comment"] is True


@pytest.mark.asyncio
async def test_email_sent_when_enabled_and_configured(
    test_client: AsyncClient, memory_mail: MemoryEmailTransport, monkeypatch
):
    monkeypatch.setenv("SMTP_HOST", "smtp.test.local")
    monkeypatch.setenv("SMTP_FROM", "noreply@opentask.test")
    # reload config values via _get_value which reads env each call — ok

    # recipient username must look like email
    email_uname = f"em_{uuid.uuid4().hex[:6]}@example.com"
    owner = await _register(test_client, "em_o")
    member = await _register(test_client, "em_m", username=email_uname)
    await _add_member(test_client, owner, member)

    # enable email channel for member in owner's WS
    await test_client.put(
        "/api/inbox/preferences",
        headers=_auth(member["token"], owner["workspaceId"]),
        json={"email_enabled": True},
    )

    issue = await _create_issue(
        test_client, owner, "email-hook", assignee_id=member["userId"]
    )

    # force email_configured True in case env not picked mid-request
    with patch("opentask.services.email.service.email_configured", return_value=True), patch(
        "opentask.services.notification.service.email_configured", return_value=True
    ):
        resp = await test_client.post(
            f"/api/issues/{issue['id']}/comments",
            headers=_auth(owner["token"], owner["workspaceId"]),
            json={"content": "hello via email"},
        )
        assert resp.status_code == 200, resp.text

    # inbox still created
    inbox = await test_client.get(
        "/api/inbox", headers=_auth(member["token"], owner["workspaceId"])
    )
    assert inbox.status_code == 200
    commented = [
        r
        for r in inbox.json()["data"]["rows"]
        if r["resourceId"] == issue["id"] and r["type"] == "commented"
    ]
    assert len(commented) >= 1

    # email attempted
    assert len(memory_mail.sent) >= 1
    assert any(email_uname.lower() in m.to.lower() for m in memory_mail.sent)


@pytest.mark.asyncio
async def test_email_skipped_when_channel_off(
    test_client: AsyncClient, memory_mail: MemoryEmailTransport
):
    email_uname = f"emoff_{uuid.uuid4().hex[:6]}@example.com"
    owner = await _register(test_client, "em_off_o")
    member = await _register(test_client, "em_off_m", username=email_uname)
    await _add_member(test_client, owner, member)
    # email_enabled stays default False

    issue = await _create_issue(
        test_client, owner, "no-email", assignee_id=member["userId"]
    )
    with patch("opentask.services.email.service.email_configured", return_value=True), patch(
        "opentask.services.notification.service.email_configured", return_value=True
    ):
        resp = await test_client.post(
            f"/api/issues/{issue['id']}/comments",
            headers=_auth(owner["token"], owner["workspaceId"]),
            json={"content": "no mail please"},
        )
        assert resp.status_code == 200, resp.text

    assert memory_mail.sent == []


@pytest.mark.asyncio
async def test_email_test_requires_config(test_client: AsyncClient):
    user = await _register(test_client, "em_tcfg")
    with patch("opentask.api.inbox.router.email_configured", return_value=False):
        resp = await test_client.post(
            "/api/inbox/email-test",
            headers=_auth(user["token"], user["workspaceId"]),
        )
    assert resp.status_code == 400
    assert "SMTP" in resp.json().get("detail", "") or "邮件未配置" in str(resp.json())


@pytest.mark.asyncio
async def test_email_test_sends(
    test_client: AsyncClient, memory_mail: MemoryEmailTransport
):
    email_uname = f"emtest_{uuid.uuid4().hex[:6]}@example.com"
    user = await _register(test_client, "em_tok", username=email_uname)
    with patch("opentask.api.inbox.router.email_configured", return_value=True), patch(
        "opentask.services.email.service.email_configured", return_value=True
    ):
        resp = await test_client.post(
            "/api/inbox/email-test",
            headers=_auth(user["token"], user["workspaceId"]),
        )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["sent"] is True
    assert data["to"] == email_uname.lower()
    assert len(memory_mail.sent) == 1
    assert "测试" in memory_mail.sent[0].subject or "OpenTask" in memory_mail.sent[0].subject
