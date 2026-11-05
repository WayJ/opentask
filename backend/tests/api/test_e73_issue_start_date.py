"""E73: Issue start_date mid — CRUD, validation, filters, audit, started_at independence."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e73"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str, **extra):
    body = {
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
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _iso(d: date) -> str:
    return datetime.combine(d, datetime.min.time()).isoformat()


@pytest.mark.asyncio
async def test_create_and_update_start_date(test_client: AsyncClient):
    user = await _register(test_client, "e73_crud")
    start = date(2026, 11, 10)
    due = date(2026, 11, 12)
    issue = await _create_issue(
        test_client,
        user,
        "With start",
        start_date=_iso(start),
        due_date=_iso(due),
    )
    assert issue.get("start_date")
    assert issue["start_date"][:10] == "2026-11-10"
    assert issue.get("started_at") in (None, "")

    resp = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"start_date": _iso(date(2026, 11, 11))},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["start_date"][:10] == "2026-11-11"
    assert data.get("started_at") in (None, "")


@pytest.mark.asyncio
async def test_started_at_still_auto_on_in_progress(test_client: AsyncClient):
    user = await _register(test_client, "e73_started")
    issue = await _create_issue(
        test_client,
        user,
        "Auto started_at",
        start_date=_iso(date(2026, 11, 1)),
    )
    assert issue.get("started_at") in (None, "")

    resp = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"status": "in_progress"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data.get("started_at"), "started_at must auto-write on in_progress"
    assert data["start_date"][:10] == "2026-11-01"


@pytest.mark.asyncio
async def test_start_after_due_400_same_day_ok(test_client: AsyncClient):
    user = await _register(test_client, "e73_val")
    # create invalid
    resp = await test_client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json={
            "title": "Bad range",
            "type": "feature",
            "status": "open",
            "priority": "medium",
            "start_date": _iso(date(2026, 11, 10)),
            "due_date": _iso(date(2026, 11, 9)),
        },
    )
    assert resp.status_code == 400, resp.text

    # same day OK
    ok = await _create_issue(
        test_client,
        user,
        "Same day",
        start_date=_iso(date(2026, 11, 10)),
        due_date=_iso(date(2026, 11, 10)),
    )
    assert ok["start_date"][:10] == "2026-11-10"

    # only start OK
    only_start = await _create_issue(
        test_client, user, "Only start", start_date=_iso(date(2026, 12, 1))
    )
    assert only_start.get("due_date") in (None, "")

    # clear start OK after create with both
    both = await _create_issue(
        test_client,
        user,
        "Clear start",
        start_date=_iso(date(2026, 11, 1)),
        due_date=_iso(date(2026, 11, 5)),
    )
    resp2 = await test_client.put(
        f"/api/issues/{both['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"start_date": None},
    )
    assert resp2.status_code == 200, resp2.text
    assert resp2.json()["data"].get("start_date") in (None, "")


@pytest.mark.asyncio
async def test_update_due_before_existing_start_400(test_client: AsyncClient):
    user = await _register(test_client, "e73_merge")
    issue = await _create_issue(
        test_client,
        user,
        "Merge validate",
        start_date=_iso(date(2026, 11, 10)),
        due_date=_iso(date(2026, 11, 20)),
    )
    resp = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"due_date": _iso(date(2026, 11, 5))},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_start_before_after_filters(test_client: AsyncClient):
    user = await _register(test_client, "e73_filt")
    early = await _create_issue(
        test_client, user, "Early", start_date=_iso(date(2026, 11, 5))
    )
    mid = await _create_issue(
        test_client, user, "Mid", start_date=_iso(date(2026, 11, 10))
    )
    late = await _create_issue(
        test_client, user, "Late", start_date=_iso(date(2026, 11, 15))
    )
    none = await _create_issue(test_client, user, "No start")

    resp = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"start_before": "2026-11-10", "page_size": 50},
    )
    assert resp.status_code == 200, resp.text
    ids = {r["id"] for r in resp.json()["data"]["rows"]}
    assert early["id"] in ids
    assert mid["id"] in ids
    assert late["id"] not in ids
    assert none["id"] not in ids

    resp2 = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"start_after": "2026-11-10", "page_size": 50},
    )
    assert resp2.status_code == 200, resp2.text
    ids2 = {r["id"] for r in resp2.json()["data"]["rows"]}
    assert early["id"] not in ids2
    assert mid["id"] in ids2
    assert late["id"] in ids2


@pytest.mark.asyncio
async def test_sort_by_start_date(test_client: AsyncClient):
    user = await _register(test_client, "e73_sort")
    await _create_issue(test_client, user, "B", start_date=_iso(date(2026, 11, 20)))
    await _create_issue(test_client, user, "A", start_date=_iso(date(2026, 11, 5)))
    resp = await test_client.get(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"sort_by": "start_date", "sort_order": "asc", "page_size": 50},
    )
    assert resp.status_code == 200, resp.text
    rows = [r for r in resp.json()["data"]["rows"] if r.get("start_date")]
    dates = [r["start_date"][:10] for r in rows]
    assert dates == sorted(dates)


@pytest.mark.asyncio
async def test_start_date_changed_timeline_no_due_notif(test_client: AsyncClient):
    user = await _register(test_client, "e73_audit")
    issue = await _create_issue(
        test_client,
        user,
        "Audit start",
        assignee_id=user["userId"],
        start_date=_iso(date(2026, 11, 1)),
    )
    resp = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"start_date": _iso(date(2026, 11, 3))},
    )
    assert resp.status_code == 200, resp.text

    tl = await test_client.get(
        f"/api/issues/{issue['id']}/timeline",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert tl.status_code == 200, tl.text
    tl_body = tl.json()["data"]
    tl_rows = tl_body.get("rows", tl_body) if isinstance(tl_body, dict) else tl_body
    actions = [
        (r.get("action_type") or r.get("actionType")) if isinstance(r, dict) else r
        for r in tl_rows
    ]
    assert "start_date_changed" in actions, actions
    assert "due_date_changed" not in actions

    # inbox should not get due_date_changed for pure start change
    inbox = await test_client.get(
        "/api/inbox",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"page_size": 50},
    )
    if inbox.status_code == 200:
        rows = inbox.json().get("data", {}).get("rows") or inbox.json().get("data") or []
        if isinstance(rows, dict):
            rows = rows.get("rows") or []
        due_types = [
            r
            for r in rows
            if isinstance(r, dict)
            and r.get("type") == "due_date_changed"
            and r.get("resourceId") == issue["id"]
        ]
        assert due_types == []
