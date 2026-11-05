"""E59: Insights multi-label OR + saved reports + digest · no-emit."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e59"):
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


def _window(days: int = 14) -> tuple[str, str]:
    start = datetime(2026, 11, 4, 0, 0, 0)
    end = start + timedelta(days=days)
    return start.isoformat(), end.isoformat()


async def _create_cycle(client: AsyncClient, user: dict, name: str = "Sprint") -> dict:
    starts, ends = _window()
    resp = await client.post(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name, "starts_at": starts, "ends_at": ends},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _activate(client: AsyncClient, user: dict, cycle_id: str) -> dict:
    resp = await client.post(
        f"/api/cycles/{cycle_id}/activate",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_issue(client: AsyncClient, user: dict, title: str, **extra) -> dict:
    body = {
        "title": title,
        "type": "feature",
        "status": "open",
        "priority": "medium",
        **extra,
    }
    resp = await client.post(
        "/api/issues",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_tag(client: AsyncClient, user: dict, name: str) -> dict:
    resp = await client.post(
        "/api/tags",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name, "color": "#ef4444"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _attach_tag(client: AsyncClient, user: dict, issue_id: str, tag_id: int) -> None:
    resp = await client.post(
        f"/api/issues/{issue_id}/tags/{tag_id}",
        headers=_auth(user["token"], user["workspaceId"]),
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# A · multi-label OR
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_label_ids_or_narrows_and_single_alias(test_client: AsyncClient):
    user = await _register(test_client, "e59_or")
    h = _auth(user["token"], user["workspaceId"])
    t_a = await _create_tag(test_client, user, "alpha")
    t_b = await _create_tag(test_client, user, "beta")
    t_c = await _create_tag(test_client, user, "gamma")
    ia = await _create_issue(test_client, user, "issue-a")
    ib = await _create_issue(test_client, user, "issue-b")
    ic = await _create_issue(test_client, user, "issue-c")
    await _attach_tag(test_client, user, ia["id"], t_a["id"])
    await _attach_tag(test_client, user, ib["id"], t_b["id"])
    await _attach_tag(test_client, user, ic["id"], t_c["id"])

    # OR: A or B → 2
    resp = await test_client.get(
        "/api/insights/summary",
        headers=h,
        params=[("labelIds", str(t_a["id"])), ("labelIds", str(t_b["id"]))],
    )
    assert resp.status_code == 200, resp.text
    total = sum(int(v) for v in resp.json()["data"]["statusCounts"].values())
    assert total == 2

    # comma form
    resp2 = await test_client.get(
        "/api/insights/summary",
        headers=h,
        params={"labelIds": f"{t_a['id']},{t_b['id']}"},
    )
    assert resp2.status_code == 200, resp2.text
    assert sum(int(v) for v in resp2.json()["data"]["statusCounts"].values()) == 2

    # single labelId alias
    resp3 = await test_client.get(
        "/api/insights/summary",
        headers=h,
        params={"labelId": t_a["id"]},
    )
    assert resp3.status_code == 200, resp3.text
    assert sum(int(v) for v in resp3.json()["data"]["statusCounts"].values()) == 1


@pytest.mark.asyncio
async def test_label_id_and_label_ids_conflict_400(test_client: AsyncClient):
    user = await _register(test_client, "e59_cfl")
    h = _auth(user["token"], user["workspaceId"])
    t = await _create_tag(test_client, user, "solo")
    resp = await test_client.get(
        "/api/insights/summary",
        headers=h,
        params={"labelId": t["id"], "labelIds": str(t["id"])},
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_label_ids_cross_tenant_404_and_export(test_client: AsyncClient):
    user = await _register(test_client, "e59_x1")
    other = await _register(test_client, "e59_x2")
    h = _auth(user["token"], user["workspaceId"])
    foreign = await _create_tag(test_client, other, "foreign")
    resp = await test_client.get(
        "/api/insights/summary",
        headers=h,
        params={"labelIds": str(foreign["id"])},
    )
    assert resp.status_code == 404, resp.text

    t = await _create_tag(test_client, user, "mine")
    issue = await _create_issue(test_client, user, "csv-me")
    await _attach_tag(test_client, user, issue["id"], t["id"])
    csv_resp = await test_client.get(
        "/api/insights/export.csv",
        headers=h,
        params={"labelIds": str(t["id"])},
    )
    assert csv_resp.status_code == 200, csv_resp.text
    assert "status" in csv_resp.text


@pytest.mark.asyncio
async def test_label_ids_narrow_cycle_snapshot(test_client: AsyncClient):
    user = await _register(test_client, "e59_cyc")
    h = _auth(user["token"], user["workspaceId"])
    cycle = await _create_cycle(test_client, user, "Cyc-E59")
    await _activate(test_client, user, cycle["id"])
    t_a = await _create_tag(test_client, user, "c-a")
    t_b = await _create_tag(test_client, user, "c-b")
    ia = await _create_issue(test_client, user, "c-ia", cycle_id=cycle["id"])
    ib = await _create_issue(test_client, user, "c-ib", cycle_id=cycle["id"])
    await _attach_tag(test_client, user, ia["id"], t_a["id"])
    await _attach_tag(test_client, user, ib["id"], t_b["id"])

    resp = await test_client.get(
        "/api/insights/summary",
        headers=h,
        params={"labelIds": f"{t_a['id']},{t_b['id']}", "cycleId": cycle["id"]},
    )
    assert resp.status_code == 200, resp.text
    snap = resp.json()["data"]["cycleSnapshot"]
    assert snap is not None
    assert snap["issueCount"] == 2

    resp2 = await test_client.get(
        "/api/insights/summary",
        headers=h,
        params={"labelIds": str(t_a["id"]), "cycleId": cycle["id"]},
    )
    assert resp2.json()["data"]["cycleSnapshot"]["issueCount"] == 1


# ---------------------------------------------------------------------------
# B · saved reports
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_saved_reports_crud_default_and_cap(test_client: AsyncClient):
    user = await _register(test_client, "e59_rpt")
    h = _auth(user["token"], user["workspaceId"])
    t = await _create_tag(test_client, user, "rpt-tag")

    create = await test_client.post(
        "/api/insights/reports",
        headers=h,
        json={
            "name": "My slice",
            "filters": {"labelIds": [t["id"]]},
            "isDefault": True,
        },
    )
    assert create.status_code == 200, create.text
    report = create.json()["data"]
    assert report["isDefault"] is True
    assert report["filters"]["labelIds"] == [t["id"]]
    rid = report["id"]

    # second default clears first
    create2 = await test_client.post(
        "/api/insights/reports",
        headers=h,
        json={"name": "Other", "filters": {}, "isDefault": True},
    )
    assert create2.status_code == 200, create2.text
    listed = await test_client.get("/api/insights/reports", headers=h)
    assert listed.status_code == 200
    rows = listed.json()["data"]["rows"]
    defaults = [r for r in rows if r["isDefault"]]
    assert len(defaults) == 1
    assert defaults[0]["id"] == create2.json()["data"]["id"]

    # apply filters → summary matches
    filt = create.json()["data"]["filters"]  # first report filters still label
    # re-fetch first
    first = next(r for r in rows if r["id"] == rid)
    assert first["isDefault"] is False
    summ = await test_client.get(
        "/api/insights/summary",
        headers=h,
        params=[("labelIds", str(x)) for x in first["filters"].get("labelIds", [])],
    )
    assert summ.status_code == 200

    patch = await test_client.patch(
        f"/api/insights/reports/{rid}",
        headers=h,
        json={"name": "Renamed", "isDefault": True},
    )
    assert patch.status_code == 200, patch.text
    assert patch.json()["data"]["name"] == "Renamed"
    assert patch.json()["data"]["isDefault"] is True

    delete = await test_client.delete(f"/api/insights/reports/{rid}", headers=h)
    assert delete.status_code == 200, delete.text
    gone = await test_client.get(f"/api/insights/reports/{rid}", headers=h)
    # no GET by id endpoint — list should not contain
    listed2 = await test_client.get("/api/insights/reports", headers=h)
    assert all(r["id"] != rid for r in listed2.json()["data"]["rows"])


@pytest.mark.asyncio
async def test_saved_report_foreign_404_and_cap20(test_client: AsyncClient):
    user = await _register(test_client, "e59_cap")
    other = await _register(test_client, "e59_capo")
    h = _auth(user["token"], user["workspaceId"])
    ho = _auth(other["token"], other["workspaceId"])

    created = await test_client.post(
        "/api/insights/reports",
        headers=h,
        json={"name": "mine", "filters": {}},
    )
    rid = created.json()["data"]["id"]

    # other workspace cannot see/patch
    bad = await test_client.patch(
        f"/api/insights/reports/{rid}",
        headers=ho,
        json={"name": "hack"},
    )
    assert bad.status_code == 404, bad.text
    bad_del = await test_client.delete(f"/api/insights/reports/{rid}", headers=ho)
    assert bad_del.status_code == 404, bad_del.text

    # fill to cap 20 (already 1)
    for i in range(19):
        resp = await test_client.post(
            "/api/insights/reports",
            headers=h,
            json={"name": f"r{i}", "filters": {}},
        )
        assert resp.status_code == 200, resp.text
    over = await test_client.post(
        "/api/insights/reports",
        headers=h,
        json={"name": "overflow", "filters": {}},
    )
    assert over.status_code == 400, over.text


# ---------------------------------------------------------------------------
# C · digest
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_digest_pref_default_off_and_tick_idempotent(test_client: AsyncClient):
    user = await _register(test_client, "e59_dig")
    h = _auth(user["token"], user["workspaceId"])

    prefs = await test_client.get("/api/inbox/preferences", headers=h)
    assert prefs.status_code == 200, prefs.text
    assert prefs.json()["data"]["insights_digest"] is False

    # tick with pref off → created 0
    tick0 = await test_client.post("/api/insights/run-digest", headers=h)
    assert tick0.status_code == 200, tick0.text
    assert tick0.json()["data"]["created"] == 0

    # enable + create default report
    put = await test_client.put(
        "/api/inbox/preferences",
        headers=h,
        json={"insights_digest": True},
    )
    assert put.status_code == 200, put.text
    assert put.json()["data"]["insights_digest"] is True

    t = await _create_tag(test_client, user, "dig-tag")
    await _create_issue(test_client, user, "dig-issue")
    await test_client.post(
        "/api/insights/reports",
        headers=h,
        json={
            "name": "Digest default",
            "filters": {"labelIds": [t["id"]]},
            "isDefault": True,
        },
    )

    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new_callable=AsyncMock,
    ) as fire_spy:
        tick1 = await test_client.post("/api/insights/run-digest", headers=h)
        assert tick1.status_code == 200, tick1.text
        assert tick1.json()["data"]["created"] == 1
        fire_spy.assert_not_called()

    inbox = await test_client.get("/api/inbox", headers=h)
    assert inbox.status_code == 200, inbox.text
    digests = [r for r in inbox.json()["data"]["rows"] if r["type"] == "insights_digest"]
    assert len(digests) == 1

    # same-day re-tick no rewrite
    tick2 = await test_client.post("/api/insights/run-digest", headers=h)
    assert tick2.status_code == 200, tick2.text
    assert tick2.json()["data"]["created"] == 0
    assert tick2.json()["data"]["skipped"] >= 1

    inbox2 = await test_client.get("/api/inbox", headers=h)
    digests2 = [r for r in inbox2.json()["data"]["rows"] if r["type"] == "insights_digest"]
    assert len(digests2) == 1
