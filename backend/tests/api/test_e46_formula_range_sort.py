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
