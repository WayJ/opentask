"""E41：Issue audit & outbound signals — timeline thicken + CSV export + CF webhook."""
from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e41"):
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


async def _create_issue(client: AsyncClient, user: dict, title: str = "e41-issue", **extra) -> dict:
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


async def _create_cycle(client: AsyncClient, user: dict, name: str = "C-e41") -> dict:
    start = datetime(2026, 11, 4, 0, 0, 0)
    end = start + timedelta(days=14)
    resp = await client.post(
        "/api/cycles",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name, "starts_at": start.isoformat(), "ends_at": end.isoformat()},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_project(client: AsyncClient, user: dict, name: str | None = None) -> dict:
    resp = await client.post(
        "/api/projects",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"name": name or f"Proj-{uuid.uuid4().hex[:6]}", "description": "e41"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _create_cf(
    client: AsyncClient, user: dict, *, name: str, key: str, type_: str, options=None, **extra
) -> dict:
    body = {"name": name, "key": key, "type": type_, **extra}
    if options is not None:
        body["options"] = options
    resp = await client.post(
        "/api/custom-fields",
        headers=_auth(user["token"], user["workspaceId"]),
        json=body,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _set_cf(client: AsyncClient, user: dict, issue_id: str, values: list) -> dict:
    resp = await client.patch(
        f"/api/issues/{issue_id}/custom-fields",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"values": values},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


async def _timeline(client: AsyncClient, user: dict, issue_id: str) -> list:
    resp = await client.get(
        f"/api/issues/{issue_id}/timeline",
        headers=_auth(user["token"], user["workspaceId"]),
        params={"limit": 100},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["rows"]


def _actions(rows: list) -> list:
    return [r.get("action_type") or r.get("actionType") for r in rows]


# ---------------------------------------------------------------------------
# A — Timeline thicken
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cycle_estimate_project_timeline_on_change(test_client: AsyncClient):
    user = await _register(test_client, "e41_cep")
    h = _auth(user["token"], user["workspaceId"])
    cycle = await _create_cycle(test_client, user)
    project = await _create_project(test_client, user)
    issue = await _create_issue(test_client, user, "cep")

    before = len(await _timeline(test_client, user, issue["id"]))

    upd = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={
            "cycle_id": cycle["id"],
            "estimate_points": 5,
            "project_id": project["id"],
        },
    )
    assert upd.status_code == 200, upd.text

    rows = await _timeline(test_client, user, issue["id"])
    acts = _actions(rows)
    assert acts.count("cycle_changed") == 1
    assert acts.count("estimate_changed") == 1
    assert acts.count("project_changed") == 1
    assert len(rows) == before + 3

    # idempotent same values → no new rows
    upd2 = await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={
            "cycle_id": cycle["id"],
            "estimate_points": 5,
            "project_id": project["id"],
        },
    )
    assert upd2.status_code == 200, upd2.text
    rows2 = await _timeline(test_client, user, issue["id"])
    assert len(rows2) == len(rows)

    # verify action_data shape
    cycle_row = next(r for r in rows if (r.get("action_type") or r.get("actionType")) == "cycle_changed")
    ad = cycle_row.get("action_data") or cycle_row.get("actionData") or {}
    assert ad.get("from") in (None, "")
    assert ad.get("to") == cycle["id"]


@pytest.mark.asyncio
async def test_cf_upsert_writes_custom_field_changed_timeline(test_client: AsyncClient):
    user = await _register(test_client, "e41_cf_tl")
    await _create_cf(
        test_client, user, name="Tier", key="tier", type_="single_select", options=["a", "b", "c"]
    )
    await _create_cf(test_client, user, name="Note", key="note", type_="text")
    issue = await _create_issue(test_client, user, "cf-tl")

    await _set_cf(
        test_client,
        user,
        issue["id"],
        [{"key": "tier", "value": "a"}, {"key": "note", "value": "hello"}],
    )
    rows = await _timeline(test_client, user, issue["id"])
    cf_rows = [r for r in rows if (r.get("action_type") or r.get("actionType")) == "custom_field_changed"]
    assert len(cf_rows) == 2
    keys = {
        (r.get("action_data") or r.get("actionData") or {}).get("fieldKey")
        or (r.get("action_data") or r.get("actionData") or {}).get("field_key")
        for r in cf_rows
    }
    assert keys == {"tier", "note"}

    # change one only
    await _set_cf(test_client, user, issue["id"], [{"key": "tier", "value": "b"}])
    rows2 = await _timeline(test_client, user, issue["id"])
    cf_rows2 = [r for r in rows2 if (r.get("action_type") or r.get("actionType")) == "custom_field_changed"]
    assert len(cf_rows2) == 3
    latest = cf_rows2[0]  # newest first
    ad = latest.get("action_data") or latest.get("actionData") or {}
    assert (ad.get("fieldKey") or ad.get("field_key")) == "tier"
    assert ad.get("from") == "a"
    assert ad.get("to") == "b"


@pytest.mark.asyncio
async def test_formula_upsert_rejected_no_timeline(test_client: AsyncClient):
    user = await _register(test_client, "e41_fml")
    await _create_cf(test_client, user, name="Weight", key="weight", type_="number")
    await _create_cf(
        test_client,
        user,
        name="Doubled",
        key="doubled",
        type_="formula",
        formulaExpr="COALESCE(cf.weight, 0) * 2",
        formulaResultType="number",
    )
    issue = await _create_issue(test_client, user, "fml")
    before = _actions(await _timeline(test_client, user, issue["id"]))

    resp = await test_client.patch(
        f"/api/issues/{issue['id']}/custom-fields",
        headers=_auth(user["token"], user["workspaceId"]),
        json={"values": [{"key": "doubled", "value": 99}]},
    )
    assert resp.status_code == 400, resp.text
    after = _actions(await _timeline(test_client, user, issue["id"]))
    assert after == before
    assert "custom_field_changed" not in after


# ---------------------------------------------------------------------------
# B — CSV export
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_issue_timeline_export_csv(test_client: AsyncClient):
    user = await _register(test_client, "e41_exp")
    h = _auth(user["token"], user["workspaceId"])
    cycle = await _create_cycle(test_client, user)
    issue = await _create_issue(test_client, user, "exp")
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"cycle_id": cycle["id"], "estimate_points": 2},
    )

    resp = await test_client.get(
        f"/api/issues/{issue['id']}/timeline/export.csv",
        headers=h,
    )
    assert resp.status_code == 200, resp.text
    assert "text/csv" in resp.headers.get("content-type", "")
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "timeline.csv" in cd
    text = resp.text
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    assert fieldnames == [
        "created_at",
        "action_type",
        "user_id",
        "user_name",
        "field_key",
        "from_value",
        "to_value",
        "action_data_json",
    ]
    rows = list(reader)
    types = {r["action_type"] for r in rows}
    assert "cycle_changed" in types
    assert "estimate_changed" in types
    assert "created" in types


@pytest.mark.asyncio
async def test_timeline_export_filter_and_truncate_header(test_client: AsyncClient):
    user = await _register(test_client, "e41_trunc")
    h = _auth(user["token"], user["workspaceId"])
    issue = await _create_issue(test_client, user, "trunc")
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"estimate_points": 1},
    )
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"estimate_points": 2},
    )

    filtered = await test_client.get(
        f"/api/issues/{issue['id']}/timeline/export.csv",
        headers=h,
        params={"actionType": "estimate_changed"},
    )
    assert filtered.status_code == 200, filtered.text
    rows = list(csv.DictReader(io.StringIO(filtered.text)))
    assert rows and all(r["action_type"] == "estimate_changed" for r in rows)

    trunc = await test_client.get(
        f"/api/issues/{issue['id']}/timeline/export.csv",
        headers=h,
        params={"limit": 1},
    )
    assert trunc.status_code == 200, trunc.text
    assert trunc.headers.get("X-OpenTask-Truncated") == "true"
    rows1 = list(csv.DictReader(io.StringIO(trunc.text)))
    assert len(rows1) == 1


@pytest.mark.asyncio
async def test_workspace_timeline_export_and_cross_tenant(test_client: AsyncClient):
    owner = await _register(test_client, "e41_ws_o")
    other = await _register(test_client, "e41_ws_x")
    h = _auth(owner["token"], owner["workspaceId"])
    issue = await _create_issue(test_client, owner, "ws-exp")
    await test_client.put(
        f"/api/issues/{issue['id']}",
        headers=h,
        json={"estimate_points": 3},
    )

    ws = await test_client.get(
        "/api/issues/timeline/export.csv",
        headers=h,
        params={"issueId": issue["id"]},
    )
    assert ws.status_code == 200, ws.text
    rows = list(csv.DictReader(io.StringIO(ws.text)))
    assert any(r["action_type"] == "estimate_changed" for r in rows)

    # other tenant cannot export owner's issue (404)
    cross = await test_client.get(
        f"/api/issues/{issue['id']}/timeline/export.csv",
        headers=_auth(other["token"], other["workspaceId"]),
    )
    assert cross.status_code == 404, cross.text


# ---------------------------------------------------------------------------
# D — Webhook issue.custom_field_changed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_webhook_accepts_custom_field_changed_event(test_client: AsyncClient):
    user = await _register(test_client, "e41_wh_ev")
    h = _auth(user["token"], user["workspaceId"])
    with patch(
        "opentask.services.workspace_webhook.service.httpx.AsyncClient"
    ) as client_cls:
        inst = AsyncMock()
        inst.__aenter__.return_value = inst
        inst.__aexit__.return_value = None

        class _R:
            status_code = 200
            text = "ok"

        inst.post = AsyncMock(return_value=_R())
        client_cls.return_value = inst

        created = await test_client.post(
            "/api/webhooks",
            headers=h,
            json={
                "url": "https://example.com/e41",
                "events": ["issue.custom_field_changed"],
                "name": "CF",
            },
        )
        assert created.status_code == 200, created.text
        assert "issue.custom_field_changed" in created.json()["data"]["events"]


@pytest.mark.asyncio
async def test_cf_change_fires_webhook_per_field(test_client: AsyncClient):
    user = await _register(test_client, "e41_wh_fire")
    h = _auth(user["token"], user["workspaceId"])
    await _create_cf(
        test_client, user, name="Tier", key="tier", type_="single_select", options=["a", "b"]
    )
    await _create_cf(test_client, user, name="Note", key="note", type_="text")
    issue = await _create_issue(test_client, user, "wh-fire")

    with patch(
        "opentask.services.workspace_webhook.service.httpx.AsyncClient"
    ) as client_cls:
        inst = AsyncMock()
        inst.__aenter__.return_value = inst
        inst.__aexit__.return_value = None

        class _R:
            status_code = 200
            text = "ok"

        inst.post = AsyncMock(return_value=_R())
        client_cls.return_value = inst

        created = await test_client.post(
            "/api/webhooks",
            headers=h,
            json={
                "url": "https://example.com/e41-fire",
                "events": ["issue.custom_field_changed"],
            },
        )
        assert created.status_code == 200, created.text

        await _set_cf(
            test_client,
            user,
            issue["id"],
            [{"key": "tier", "value": "a"}, {"key": "note", "value": "x"}],
        )

        assert inst.post.await_count >= 2
        bodies = []
        for call in inst.post.await_args_list:
            # kwargs content or args
            kwargs = call.kwargs
            content = kwargs.get("content") or kwargs.get("data")
            if content is None and call.args:
                # positional json?
                pass
            if content is None:
                content = kwargs.get("json")
            bodies.append(content)

        # Prefer reading from delivery via re-fetch of call content bytes
        import json as _json

        parsed = []
        for call in inst.post.await_args_list:
            kwargs = call.kwargs
            raw = kwargs.get("content")
            if raw is None:
                continue
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            parsed.append(_json.loads(raw))

        cf_events = [p for p in parsed if p.get("type") == "issue.custom_field_changed"]
        assert len(cf_events) == 2, parsed
        keys = {e["data"]["fieldKey"] for e in cf_events}
        assert keys == {"tier", "note"}
        for e in cf_events:
            assert e["data"]["id"] == issue["id"]
            assert e["data"]["issueCode"] == issue["issue_code"]
