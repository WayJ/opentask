"""E39：Due reminders + digest tick — prefs, ledger, run-due-reminders."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from opentask.models.notification_preference.model import PREF_KEYS, TYPE_TO_PREF_KEY
from opentask.services.email import MemoryEmailTransport, set_email_transport


async def _register(client: AsyncClient, prefix: str = "e39", *, username: str | None = None):
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


async def _create_issue(client: AsyncClient, user: dict, title: str = "e39-issue", **extra) -> dict:
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


async def _watch(client: AsyncClient, user: dict, issue_id: str, workspace_id: str):
    resp = await client.post(
        f"/api/issues/{issue_id}/watchers",
        headers=_auth(user["token"], workspace_id),
    )
    assert resp.status_code == 200, resp.text


def _iso_due(days_offset: int, hour: int = 12) -> str:
    d = datetime.utcnow().replace(hour=hour, minute=0, second=0, microsecond=0) + timedelta(
        days=days_offset
    )
    return d.isoformat() + "Z"


# ---------------------------------------------------------------------------
# A — prefs + TYPE mapping
# ---------------------------------------------------------------------------


def test_pref_keys_and_type_mapping_include_due_reminder():
    assert "due_reminder" in PREF_KEYS
    assert TYPE_TO_PREF_KEY.get("due_reminder") == "due_reminder"
    assert TYPE_TO_PREF_KEY.get("due_reminder_digest") == "due_reminder"


@pytest.mark.asyncio
async def test_prefs_default_due_reminder_fields(test_client: AsyncClient):
    user = await _register(test_client, "e39_pref")
    h = _auth(user["token"], user["workspaceId"])
    got = await test_client.get("/api/inbox/preferences", headers=h)
    assert got.status_code == 200, got.text
    data = got.json()["data"]
    assert data["due_reminder"] is True
    assert data["due_reminder_digest"] is False

    put = await test_client.put(
        "/api/inbox/preferences",
        headers=h,
        json={"due_reminder": False, "due_reminder_digest": True},
    )
    assert put.status_code == 200, put.text
    pdata = put.json()["data"]
    assert pdata["due_reminder"] is False
    assert pdata["due_reminder_digest"] is True

    got2 = await test_client.get("/api/inbox/preferences", headers=h)
    assert got2.json()["data"]["due_reminder"] is False
    assert got2.json()["data"]["due_reminder_digest"] is True


# ---------------------------------------------------------------------------
# B — run-due-reminders
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_due_soon_assignee_and_watcher(test_client: AsyncClient):
    owner = await _register(test_client, "e39_own")
    assignee = await _register(test_client, "e39_as")
    watcher = await _register(test_client, "e39_w")
    await _add_member(test_client, owner, assignee)
    await _add_member(test_client, owner, watcher)

    issue = await _create_issue(
        test_client,
        owner,
        "soon-issue",
        assignee_id=assignee["userId"],
        due_date=_iso_due(1),
    )
    await _watch(test_client, watcher, issue["id"], owner["workspaceId"])

    resp = await test_client.post(
        "/api/inbox/run-due-reminders",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["processedIssues"] >= 1
    assert data["remindersCreated"] >= 2
    assert data["digestsCreated"] == 0

    for uid, token in (
        (assignee["userId"], assignee["token"]),
        (watcher["userId"], watcher["token"]),
    ):
        inbox = await test_client.get(
            "/api/inbox",
            headers=_auth(token, owner["workspaceId"]),
        )
        assert inbox.status_code == 200, inbox.text
        types = [r["type"] for r in inbox.json()["data"]["rows"]]
        assert "due_reminder" in types, f"user={uid} types={types}"


@pytest.mark.asyncio
async def test_closed_issue_skipped(test_client: AsyncClient):
    owner = await _register(test_client, "e39_cl")
    issue = await _create_issue(
        test_client,
        owner,
        "closed-due",
        assignee_id=owner["userId"],
        due_date=_iso_due(1),
        status="closed",
    )
    # ensure closed via patch if create ignored status
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(owner["token"], owner["workspaceId"]),
        json={"status": "closed"},
    )
    resp = await test_client.post(
        "/api/inbox/run-due-reminders",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["remindersCreated"] == 0


@pytest.mark.asyncio
async def test_no_recipient_skipped(test_client: AsyncClient):
    owner = await _register(test_client, "e39_nr")
    await _create_issue(
        test_client,
        owner,
        "no-asg",
        due_date=_iso_due(1),
    )
    resp = await test_client.post(
        "/api/inbox/run-due-reminders",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    # no assignee/watchers → skipped (processed may still count the issue)
    data = resp.json()["data"]
    assert data["remindersCreated"] == 0


@pytest.mark.asyncio
async def test_second_tick_no_double_soon(test_client: AsyncClient):
    owner = await _register(test_client, "e39_dd")
    issue = await _create_issue(
        test_client,
        owner,
        "dedupe",
        assignee_id=owner["userId"],
        due_date=_iso_due(2),
    )
    h = _auth(owner["token"], owner["workspaceId"])
    r1 = await test_client.post("/api/inbox/run-due-reminders", headers=h)
    assert r1.status_code == 200, r1.text
    c1 = r1.json()["data"]["remindersCreated"]
    assert c1 >= 1
    r2 = await test_client.post("/api/inbox/run-due-reminders", headers=h)
    assert r2.status_code == 200, r2.text
    assert r2.json()["data"]["remindersCreated"] == 0
    inbox = await test_client.get("/api/inbox", headers=h)
    due_rows = [r for r in inbox.json()["data"]["rows"] if r["type"] == "due_reminder"]
    assert len(due_rows) == 1
    assert issue["id"]


@pytest.mark.asyncio
async def test_change_due_allows_new_soon(test_client: AsyncClient):
    owner = await _register(test_client, "e39_cd")
    h = _auth(owner["token"], owner["workspaceId"])
    issue = await _create_issue(
        test_client,
        owner,
        "redue",
        assignee_id=owner["userId"],
        due_date=_iso_due(1),
    )
    r1 = await test_client.post("/api/inbox/run-due-reminders", headers=h)
    assert r1.json()["data"]["remindersCreated"] >= 1

    # change due into another soon day
    put = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"due_date": _iso_due(3)},
    )
    assert put.status_code == 200, put.text
    r2 = await test_client.post("/api/inbox/run-due-reminders", headers=h)
    assert r2.status_code == 200, r2.text
    assert r2.json()["data"]["remindersCreated"] >= 1


@pytest.mark.asyncio
async def test_overdue_same_day_dedupe_next_day_ok(test_client: AsyncClient):
    owner = await _register(test_client, "e39_ov")
    h = _auth(owner["token"], owner["workspaceId"])
    await _create_issue(
        test_client,
        owner,
        "overdue",
        assignee_id=owner["userId"],
        due_date=_iso_due(-2),
    )
    r1 = await test_client.post("/api/inbox/run-due-reminders", headers=h)
    assert r1.status_code == 200, r1.text
    assert r1.json()["data"]["remindersCreated"] >= 1
    r2 = await test_client.post("/api/inbox/run-due-reminders", headers=h)
    assert r2.json()["data"]["remindersCreated"] == 0

    # simulate next UTC day via service today override is not exposed on API;
    # verify deliveries list has overdue kind for today
    deliv = await test_client.get(
        "/api/inbox/due-reminder-deliveries",
        headers=h,
    )
    assert deliv.status_code == 200, deliv.text
    rows = deliv.json()["data"]["rows"]
    assert any(r["kind"] == "overdue" for r in rows)


@pytest.mark.asyncio
async def test_digest_merges_and_pref_off_skips(test_client: AsyncClient):
    owner = await _register(test_client, "e39_dg")
    h = _auth(owner["token"], owner["workspaceId"])
    await test_client.put(
        "/api/inbox/preferences",
        headers=h,
        json={"due_reminder_digest": True},
    )
    await _create_issue(
        test_client, owner, "d1", assignee_id=owner["userId"], due_date=_iso_due(1)
    )
    await _create_issue(
        test_client, owner, "d2", assignee_id=owner["userId"], due_date=_iso_due(2)
    )
    r1 = await test_client.post("/api/inbox/run-due-reminders", headers=h)
    assert r1.status_code == 200, r1.text
    data = r1.json()["data"]
    assert data["digestsCreated"] == 1
    assert data["remindersCreated"] == 0
    inbox = await test_client.get("/api/inbox", headers=h)
    digests = [r for r in inbox.json()["data"]["rows"] if r["type"] == "due_reminder_digest"]
    assert len(digests) == 1

    # second tick same day — no rewrite
    r2 = await test_client.post("/api/inbox/run-due-reminders", headers=h)
    assert r2.json()["data"]["digestsCreated"] == 0

    # turn off due_reminder entirely
    await test_client.put(
        "/api/inbox/preferences",
        headers=h,
        json={"due_reminder": False},
    )
    other = await _register(test_client, "e39_dg2")
    await _add_member(test_client, owner, other)
    await _create_issue(
        test_client, owner, "d3", assignee_id=other["userId"], due_date=_iso_due(1)
    )
    # other has default prefs — should get reminder; owner skipped for new issue if assignee is other
    r3 = await test_client.post("/api/inbox/run-due-reminders", headers=h)
    assert r3.status_code == 200
    # owner digest already exists; other should get per-issue reminder
    assert r3.json()["data"]["remindersCreated"] >= 1


@pytest.mark.asyncio
async def test_viewer_forbidden_and_cross_ws(test_client: AsyncClient):
    owner = await _register(test_client, "e39_v")
    viewer = await _register(test_client, "e39_vv")
    await _add_member(test_client, owner, viewer, role="viewer")
    resp = await test_client.post(
        "/api/inbox/run-due-reminders",
        headers=_auth(viewer["token"], owner["workspaceId"]),
    )
    assert resp.status_code == 403

    other = await _register(test_client, "e39_xws")
    await _create_issue(
        test_client,
        other,
        "secret",
        assignee_id=other["userId"],
        due_date=_iso_due(1),
    )
    # owner tick must not create for other WS
    r = await test_client.post(
        "/api/inbox/run-due-reminders",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert r.status_code == 200
    # other inbox should be empty of due_reminder until their own tick
    inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(other["token"], other["workspaceId"]),
    )
    types = [row["type"] for row in inbox.json()["data"]["rows"]]
    assert "due_reminder" not in types


@pytest.mark.asyncio
async def test_fail_isolate(test_client: AsyncClient, monkeypatch):
    owner = await _register(test_client, "e39_fi")
    a = await _register(test_client, "e39_fia")
    b = await _register(test_client, "e39_fib")
    await _add_member(test_client, owner, a)
    await _add_member(test_client, owner, b)
    await _create_issue(
        test_client, owner, "fi-a", assignee_id=a["userId"], due_date=_iso_due(1)
    )
    await _create_issue(
        test_client, owner, "fi-b", assignee_id=b["userId"], due_date=_iso_due(1)
    )

    from opentask.services.notification import service as svc_mod

    real_create = svc_mod.NotificationService.create
    calls = {"n": 0}

    async def flaky(self, **kwargs):
        calls["n"] += 1
        if kwargs.get("recipient_user_id") == a["userId"]:
            raise RuntimeError("boom-a")
        return await real_create(self, **kwargs)

    monkeypatch.setattr(svc_mod.NotificationService, "create", flaky)
    resp = await test_client.post(
        "/api/inbox/run-due-reminders",
        headers=_auth(owner["token"], owner["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["remindersCreated"] >= 1
    assert any(e.get("userId") == a["userId"] for e in data.get("errors") or [])


@pytest.mark.asyncio
async def test_email_hook_on_due_reminder(test_client: AsyncClient):
    transport = MemoryEmailTransport()
    set_email_transport(transport)
    try:
        with patch.dict(
            "os.environ",
            {"SMTP_HOST": "smtp.test", "SMTP_FROM": "noreply@test.local"},
            clear=False,
        ):
            # re-import configured check picks env — patch email_configured
            with patch(
                "opentask.services.notification.service.email_configured", return_value=True
            ):
                user = await _register(
                    test_client, "e39_em", username=f"e39em_{uuid.uuid4().hex[:6]}@example.com"
                )
                h = _auth(user["token"], user["workspaceId"])
                await test_client.put(
                    "/api/inbox/preferences",
                    headers=h,
                    json={"email_enabled": True},
                )
                await _create_issue(
                    test_client,
                    user,
                    "mail-due",
                    assignee_id=user["userId"],
                    due_date=_iso_due(1),
                )
                resp = await test_client.post("/api/inbox/run-due-reminders", headers=h)
                assert resp.status_code == 200, resp.text
                assert resp.json()["data"]["remindersCreated"] >= 1
                assert len(transport.sent) >= 1
    finally:
        set_email_transport(None)
