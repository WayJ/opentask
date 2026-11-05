"""E43：Formula surfaces — filter / cache / swimlane prefs / no-emit."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e43"):
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


async def _setup_weight_score(client: AsyncClient, user: dict):
    h = _auth(user["token"], user["workspaceId"])
    w = await client.post(
        "/api/custom-fields",
        headers=h,
        json={"name": "Weight", "type": "number", "key": "weight"},
    )
    assert w.status_code == 200, w.text
    s = await client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "Score",
            "type": "formula",
            "key": "score",
            "formulaExpr": "COALESCE(cf.weight, 0) * 2",
            "formulaResultType": "number",
        },
    )
    assert s.status_code == 200, s.text
    return w.json()["data"], s.json()["data"], h


@pytest.mark.asyncio
async def test_coerce_formula_by_result_type():
    from opentask.models.custom_field.model import CustomField
    from opentask.services.custom_field.service import coerce_cf_filter_value

    f = CustomField(
        id="x",
        workspace_id="w",
        name="Score",
        key="score",
        type="formula",
        formula_result_type="number",
    )
    assert coerce_cf_filter_value(f, "10") == 10
    assert coerce_cf_filter_value(f, "10.5") == 10.5

    f.formula_result_type = "boolean"
    assert coerce_cf_filter_value(f, "true") is True
    assert coerce_cf_filter_value(f, "no") is False

    f.formula_result_type = "text"
    assert coerce_cf_filter_value(f, "Hello") == "Hello"

    f.formula_result_type = None
    assert coerce_cf_filter_value(f, "3") == 3


@pytest.mark.asyncio
async def test_list_filter_formula_equality(test_client: AsyncClient):
    user = await _register(test_client, "e43f")
    weight, score, h = await _setup_weight_score(test_client, user)

    a = await _create_issue(test_client, user, "hit")
    b = await _create_issue(test_client, user, "miss")
    await test_client.patch(
        f"/api/issues/{a['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": weight["id"], "value": 5}]},
    )
    await test_client.patch(
        f"/api/issues/{b['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": weight["id"], "value": 3}]},
    )

    resp = await test_client.get("/api/issues", headers=h, params={"cf.score": "10"})
    assert resp.status_code == 200, resp.text
    ids = {r["id"] for r in resp.json()["data"]["rows"]}
    assert a["id"] in ids
    assert b["id"] not in ids


@pytest.mark.asyncio
async def test_list_filter_formula_and_number_cf(test_client: AsyncClient):
    user = await _register(test_client, "e43and")
    weight, score, h = await _setup_weight_score(test_client, user)
    a = await _create_issue(test_client, user, "both")
    b = await _create_issue(test_client, user, "score-only-wrong-weight")
    await test_client.patch(
        f"/api/issues/{a['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": weight["id"], "value": 5}]},
    )
    await test_client.patch(
        f"/api/issues/{b['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": weight["id"], "value": 5}]},
    )
    # also create a plain number CF "priority_n" for AND
    pn = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={"name": "PN", "type": "number", "key": "pn"},
        )
    ).json()["data"]
    await test_client.patch(
        f"/api/issues/{a['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": pn["id"], "value": 1}]},
    )
    await test_client.patch(
        f"/api/issues/{b['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": pn["id"], "value": 2}]},
    )

    resp = await test_client.get(
        "/api/issues",
        headers=h,
        params={"cf.score": "10", "cf.pn": "1"},
    )
    assert resp.status_code == 200, resp.text
    ids = {r["id"] for r in resp.json()["data"]["rows"]}
    assert ids == {a["id"]}


@pytest.mark.asyncio
async def test_list_filter_formula_error_and_null_no_match(test_client: AsyncClient):
    user = await _register(test_client, "e43err")
    h = _auth(user["token"], user["workspaceId"])
    # formula that divides by zero when weight missing / 0
    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={"name": "Weight", "type": "number", "key": "weight"},
    )
    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "Ratio",
            "type": "formula",
            "key": "ratio",
            "formulaExpr": "1 / cf.weight",
            "formulaResultType": "number",
        },
    )
    await _create_issue(test_client, user, "no-weight")  # weight null → error
    resp = await test_client.get("/api/issues", headers=h, params={"cf.ratio": "1"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["rows"] == []


@pytest.mark.asyncio
async def test_list_filter_formula_unknown_key_empty(test_client: AsyncClient):
    user = await _register(test_client, "e43uk")
    h = _auth(user["token"], user["workspaceId"])
    await _create_issue(test_client, user, "x")
    resp = await test_client.get("/api/issues", headers=h, params={"cf.nosuch": "1"})
    assert resp.status_code == 200
    assert resp.json()["data"]["rows"] == []


@pytest.mark.asyncio
async def test_list_filter_formula_cap_400(test_client: AsyncClient, monkeypatch):
    user = await _register(test_client, "e43cap")
    weight, score, h = await _setup_weight_score(test_client, user)
    for i in range(3):
        iss = await _create_issue(test_client, user, f"c{i}")
        await test_client.patch(
            f"/api/issues/{iss['id']}/custom-fields",
            headers=h,
            json={"values": [{"fieldId": weight["id"], "value": 1}]},
        )

    import opentask.services.custom_field.service as svc

    monkeypatch.setattr(svc, "FORMULA_FILTER_CANDIDATE_CAP", 2)
    resp = await test_client.get("/api/issues", headers=h, params={"cf.score": "2"})
    assert resp.status_code == 400, resp.text
    detail = resp.json().get("detail")
    if isinstance(detail, dict):
        assert detail.get("code") == "formula_filter_too_broad"
    else:
        assert "formula_filter_too_broad" in str(detail)


@pytest.mark.asyncio
async def test_list_filter_formula_cross_ws_empty(test_client: AsyncClient):
    u1 = await _register(test_client, "e43w1")
    u2 = await _register(test_client, "e43w2")
    weight, score, h1 = await _setup_weight_score(test_client, u1)
    a = await _create_issue(test_client, u1, "ws1")
    await test_client.patch(
        f"/api/issues/{a['id']}/custom-fields",
        headers=h1,
        json={"values": [{"fieldId": weight["id"], "value": 5}]},
    )
    h2 = _auth(u2["token"], u2["workspaceId"])
    resp = await test_client.get("/api/issues", headers=h2, params={"cf.score": "10"})
    assert resp.status_code == 200
    assert resp.json()["data"]["rows"] == []


@pytest.mark.asyncio
async def test_dep_upsert_emits_number_not_formula(test_client: AsyncClient):
    """Changing weight emits CF changed for weight; formula result must NOT emit."""
    user = await _register(test_client, "e43em")
    weight, score, h = await _setup_weight_score(test_client, user)
    iss = await _create_issue(test_client, user, "emit")

    calls: list[dict] = []

    async def _spy_fire_webhooks(db, *, workspace_id, event_type, data):
        calls.append({"event_type": event_type, "data": data})

    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new=AsyncMock(side_effect=_spy_fire_webhooks),
    ):
        # also patch the import site used inside _emit
        with patch(
            "opentask.services.custom_field.service.CustomFieldService._emit_custom_field_changed",
            new=AsyncMock(),
        ) as emit:
            await test_client.patch(
                f"/api/issues/{iss['id']}/custom-fields",
                headers=h,
                json={"values": [{"fieldId": weight["id"], "value": 4}]},
            )
            assert emit.await_count == 1
            kwargs = emit.await_args.kwargs
            keys = [c["field_key"] for c in kwargs["changes"]]
            assert keys == ["weight"]
            assert "score" not in keys


@pytest.mark.asyncio
async def test_prefs_accept_formula_swimlane(test_client: AsyncClient):
    user = await _register(test_client, "e43sw")
    weight, score, h = await _setup_weight_score(test_client, user)
    body = {
        "view_mode": "board",
        "group_by": "none",
        "swimlane_by": "cf:score",
        "hide_empty_lanes": False,
        "fields": {
            "assignee": True,
            "priority": True,
            "labels": True,
            "estimate_points": True,
            "due_date": False,
            "project": False,
            "cycle": False,
            "issue_code": True,
            "type": False,
        },
        "custom_field_keys": [],
    }
    resp = await test_client.put("/api/display-prefs/issue", headers=h, json={"display": body})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]["display"]
    assert data["swimlane_by"] == "cf:score"
    assert "score" in data["custom_field_keys"]


@pytest.mark.asyncio
async def test_formula_cache_populated_after_dep_upsert(test_client: AsyncClient):
    user = await _register(test_client, "e43ca")
    weight, score, h = await _setup_weight_score(test_client, user)
    iss = await _create_issue(test_client, user, "cached")
    await test_client.patch(
        f"/api/issues/{iss['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": weight["id"], "value": 5}]},
    )

    from opentask.models.custom_field.model import IssueFormulaCache
    from opentask.repositories.base import SessionCreator
    from sqlalchemy import select

    async with SessionCreator() as db:
        rows = (
            await db.execute(
                select(IssueFormulaCache).where(
                    IssueFormulaCache.issue_id == iss["id"],
                    IssueFormulaCache.field_id == score["id"],
                )
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].error is None
        assert rows[0].value_json == 10


@pytest.mark.asyncio
async def test_formula_def_update_invalidates_cache(test_client: AsyncClient):
    user = await _register(test_client, "e43inv")
    weight, score, h = await _setup_weight_score(test_client, user)
    iss = await _create_issue(test_client, user, "inv")
    await test_client.patch(
        f"/api/issues/{iss['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": weight["id"], "value": 5}]},
    )
    # update formula expr
    resp = await test_client.patch(
        f"/api/custom-fields/{score['id']}",
        headers=h,
        json={"formulaExpr": "COALESCE(cf.weight, 0) * 3", "formulaResultType": "number"},
    )
    assert resp.status_code == 200, resp.text

    from opentask.models.custom_field.model import IssueFormulaCache
    from opentask.repositories.base import SessionCreator
    from sqlalchemy import select, func

    async with SessionCreator() as db:
        n = (
            await db.execute(
                select(func.count()).select_from(IssueFormulaCache).where(
                    IssueFormulaCache.field_id == score["id"],
                )
            )
        ).scalar()
        assert n == 0

    # filter should still work via re-eval (score=15)
    resp = await test_client.get("/api/issues", headers=h, params={"cf.score": "15"})
    assert resp.status_code == 200, resp.text
    ids = {r["id"] for r in resp.json()["data"]["rows"]}
    assert iss["id"] in ids
