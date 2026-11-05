"""E46：Formula query surfaces v2 — range / sort / no-emit."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e46"):
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


def test_parse_cf_ops():
    from opentask.services.custom_field.service import parse_cf_query_items

    items = parse_cf_query_items(
        [
            ("cf.score[gte]", "8"),
            ("cf.score[lt]", "20"),
            ("cf.weight", "5"),
            ("cf", "risk[gt]=3"),
            ("cf", "env=prod"),
        ]
    )
    assert items == [
        ("score", "gte", "8"),
        ("score", "lt", "20"),
        ("weight", "eq", "5"),
        ("risk", "gt", "3"),
        ("env", "eq", "prod"),
    ]


def test_parse_cf_ops_invalid_bracket_skipped():
    from opentask.services.custom_field.service import parse_cf_query_items

    items = parse_cf_query_items(
        [
            ("cf.score[nope]", "1"),
            ("cf.ok", "2"),
        ]
    )
    assert items == [("ok", "eq", "2")]


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
async def test_stored_number_range_and_unsupported(test_client: AsyncClient):
    user = await _register(test_client, "e46n")
    h = _auth(user["token"], user["workspaceId"])
    weight = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={"name": "Weight", "type": "number", "key": "weight"},
        )
    ).json()["data"]
    text_f = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={"name": "Note", "type": "text", "key": "note"},
        )
    ).json()["data"]
    assert weight and text_f

    a = await _create_issue(test_client, user, "low")
    b = await _create_issue(test_client, user, "mid")
    c = await _create_issue(test_client, user, "high")
    for issue, val in ((a, 3), (b, 7), (c, 12)):
        r = await test_client.patch(
            f"/api/issues/{issue['id']}/custom-fields",
            headers=h,
            json={"values": [{"fieldId": weight["id"], "value": val}]},
        )
        assert r.status_code == 200, r.text

    # gte=5 AND lt=10 → only mid
    resp = await test_client.get(
        "/api/issues",
        headers=h,
        params=[("cf.weight[gte]", "5"), ("cf.weight[lt]", "10"), ("page_size", "50")],
    )
    assert resp.status_code == 200, resp.text
    ids = {row["id"] for row in resp.json()["data"]["rows"]}
    assert ids == {b["id"]}

    # text range → 400
    bad = await test_client.get(
        "/api/issues",
        headers=h,
        params=[("cf.note[gt]", "a"), ("page_size", "50")],
    )
    assert bad.status_code == 400
    detail = bad.json().get("detail") or bad.json()
    if isinstance(detail, dict):
        code = detail.get("code") or (detail.get("detail") or {}).get("code")
    else:
        # FastAPI may wrap
        code = None
        if isinstance(detail, dict):
            code = detail.get("code")
        elif isinstance(bad.json().get("detail"), dict):
            code = bad.json()["detail"].get("code")
    body = bad.json()
    # accept either {"detail":{"code":...}} or envelope
    blob = str(body)
    assert "cf_range_unsupported" in blob

    # eq regression
    resp = await test_client.get(
        "/api/issues", headers=h, params={"cf.weight": "7", "page_size": 50}
    )
    assert resp.status_code == 200
    assert {row["id"] for row in resp.json()["data"]["rows"]} == {b["id"]}


@pytest.mark.asyncio
async def test_stored_date_range(test_client: AsyncClient):
    user = await _register(test_client, "e46d")
    h = _auth(user["token"], user["workspaceId"])
    due = (
        await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={"name": "Ship", "type": "date", "key": "ship"},
        )
    ).json()["data"]
    a = await _create_issue(test_client, user, "early")
    b = await _create_issue(test_client, user, "late")
    await test_client.patch(
        f"/api/issues/{a['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": due["id"], "value": "2026-01-10"}]},
    )
    await test_client.patch(
        f"/api/issues/{b['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": due["id"], "value": "2026-03-01"}]},
    )
    resp = await test_client.get(
        "/api/issues",
        headers=h,
        params=[("cf.ship[gte]", "2026-02-01"), ("page_size", "50")],
    )
    assert resp.status_code == 200, resp.text
    ids = {row["id"] for row in resp.json()["data"]["rows"]}
    assert ids == {b["id"]}


@pytest.mark.asyncio
async def test_formula_range_and_no_emit(test_client: AsyncClient):
    user = await _register(test_client, "e46f")
    weight, score, h = await _setup_weight_score(test_client, user)
    a = await _create_issue(test_client, user, "hit")
    b = await _create_issue(test_client, user, "miss")
    await test_client.patch(
        f"/api/issues/{a['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": weight["id"], "value": 5}]},  # score 10
    )
    await test_client.patch(
        f"/api/issues/{b['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": weight["id"], "value": 2}]},  # score 4
    )

    with patch(
        "opentask.services.workspace_webhook.service.fire_webhooks",
        new_callable=AsyncMock,
    ) as fw:
        with patch(
            "opentask.services.custom_field.service.CustomFieldService._emit_custom_field_changed",
            new_callable=AsyncMock,
        ) as em:
            resp = await test_client.get(
                "/api/issues",
                headers=h,
                params=[("cf.score[gte]", "8"), ("cf.score[lt]", "20"), ("page_size", "50")],
            )
            assert resp.status_code == 200, resp.text
            ids = {row["id"] for row in resp.json()["data"]["rows"]}
            assert ids == {a["id"]}
            fw.assert_not_called()
            em.assert_not_called()

    # AND with eq
    resp = await test_client.get(
        "/api/issues",
        headers=h,
        params=[("cf.score[gte]", "8"), ("cf.score", "10"), ("page_size", "50")],
    )
    assert resp.status_code == 200
    assert {row["id"] for row in resp.json()["data"]["rows"]} == {a["id"]}


@pytest.mark.asyncio
async def test_sort_by_cf_formula_desc_nulls_last(test_client: AsyncClient):
    user = await _register(test_client, "e46s")
    weight, score, h = await _setup_weight_score(test_client, user)
    low = await _create_issue(test_client, user, "low")
    high = await _create_issue(test_client, user, "high")
    bare = await _create_issue(test_client, user, "bare")  # no weight → score 0? COALESCE 0*2=0
    await test_client.patch(
        f"/api/issues/{low['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": weight["id"], "value": 2}]},  # 4
    )
    await test_client.patch(
        f"/api/issues/{high['id']}/custom-fields",
        headers=h,
        json={"values": [{"fieldId": weight["id"], "value": 9}]},  # 18
    )
    # bare keeps default 0 via COALESCE

    resp = await test_client.get(
        "/api/issues",
        headers=h,
        params={"sort_by": "cf:score", "sort_order": "desc", "page_size": 50},
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()["data"]["rows"]
    ids = [r["id"] for r in rows]
    assert ids.index(high["id"]) < ids.index(low["id"]) < ids.index(bare["id"])


@pytest.mark.asyncio
async def test_sort_by_cf_multi_select_unsupported(test_client: AsyncClient):
    user = await _register(test_client, "e46ms")
    h = _auth(user["token"], user["workspaceId"])
    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "Tags",
            "key": "tags",
            "type": "multi_select",
            "options": [{"value": "a", "label": "A"}],
        },
    )
    await _create_issue(test_client, user, "x")
    resp = await test_client.get(
        "/api/issues", headers=h, params={"sort_by": "cf:tags", "page_size": 10}
    )
    assert resp.status_code == 400
    assert "cf_sort_unsupported" in str(resp.json())


@pytest.mark.asyncio
async def test_sort_by_cf_cap_too_broad(test_client: AsyncClient, monkeypatch):
    user = await _register(test_client, "e46cap")
    weight, score, h = await _setup_weight_score(test_client, user)
    for i in range(3):
        iss = await _create_issue(test_client, user, f"c{i}")
        await test_client.patch(
            f"/api/issues/{iss['id']}/custom-fields",
            headers=h,
            json={"values": [{"fieldId": weight["id"], "value": i + 1}]},
        )
    import opentask.services.custom_field.service as svc
    import opentask.services.issue_service as issue_svc

    monkeypatch.setattr(svc, "FORMULA_SORT_CANDIDATE_CAP", 2)
    monkeypatch.setattr(issue_svc, "FORMULA_SORT_CANDIDATE_CAP", 2)
    resp = await test_client.get(
        "/api/issues",
        headers=h,
        params={"sort_by": "cf:score", "sort_order": "asc", "page_size": 50},
    )
    assert resp.status_code == 400
    assert "formula_sort_too_broad" in str(resp.json())


@pytest.mark.asyncio
async def test_saved_view_sort_json_cf(test_client: AsyncClient):
    user = await _register(test_client, "e46sv")
    weight, score, h = await _setup_weight_score(test_client, user)
    resp = await test_client.post(
        "/api/saved-views",
        headers=h,
        json={
            "name": "by-score",
            "filters": {},
            "sort": {"sort_by": "cf:score", "sort_order": "desc"},
            "display": {
                "view_mode": "list",
                "group_by": "none",
                "swimlane_by": "none",
                "hide_empty_lanes": False,
                "fields": {},
                "custom_field_keys": [],
            },
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()["data"]
    assert body["sort"]["sort_by"] == "cf:score"
    assert body["sort"]["sort_order"] == "desc"
