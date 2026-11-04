"""E40：Formula custom fields — create/DAG/eval/validate/upsert-readonly."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, prefix: str = "e40"):
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


async def _create_issue(
    client: AsyncClient,
    user: dict,
    title: str = "e40-issue",
    **extra,
) -> dict:
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


@pytest.mark.asyncio
async def test_create_formula_field_ok(test_client: AsyncClient):
    user = await _register(test_client, "e40_ok")
    h = _auth(user["token"], user["workspaceId"])

    # dependency number field
    w = await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={"name": "Weight", "type": "number", "key": "weight"},
    )
    assert w.status_code == 200, w.text

    created = await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "Score",
            "type": "formula",
            "key": "score",
            "formulaExpr": 'COALESCE(cf.weight, 0) * 2',
            "formulaResultType": "number",
        },
    )
    assert created.status_code == 200, created.text
    row = created.json()["data"]
    assert row["type"] == "formula"
    assert row["key"] == "score"
    assert row["formulaExpr"] == "COALESCE(cf.weight, 0) * 2"
    assert row["formulaResultType"] == "number"
    assert row["options"] == []


@pytest.mark.asyncio
async def test_create_formula_missing_expr_400(test_client: AsyncClient):
    user = await _register(test_client, "e40_mx")
    h = _auth(user["token"], user["workspaceId"])
    resp = await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={"name": "Bad", "type": "formula", "formulaResultType": "number"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_non_formula_cannot_carry_expr(test_client: AsyncClient):
    user = await _register(test_client, "e40_nf")
    h = _auth(user["token"], user["workspaceId"])
    resp = await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "Plain",
            "type": "number",
            "formulaExpr": "1+1",
            "formulaResultType": "number",
        },
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_formula_cycle_rejected(test_client: AsyncClient):
    user = await _register(test_client, "e40_cy")
    h = _auth(user["token"], user["workspaceId"])

    a = await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "A",
            "type": "formula",
            "key": "fa",
            "formulaExpr": "1",
            "formulaResultType": "number",
        },
    )
    assert a.status_code == 200, a.text
    aid = a.json()["data"]["id"]

    b = await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "B",
            "type": "formula",
            "key": "fb",
            "formulaExpr": "cf.fa + 1",
            "formulaResultType": "number",
        },
    )
    assert b.status_code == 200, b.text

    # update A to depend on B → cycle
    patched = await test_client.patch(
        f"/api/custom-fields/{aid}",
        headers=h,
        json={"formulaExpr": "cf.fb + 1"},
    )
    assert patched.status_code == 400


@pytest.mark.asyncio
async def test_formula_depth_limit(test_client: AsyncClient):
    user = await _register(test_client, "e40_dp")
    h = _auth(user["token"], user["workspaceId"])

    # chain f0=1; f1=cf.f0; ... f9 would be depth 9 from f9 looking at deps
    prev = None
    for i in range(9):
        key = f"d{i}"
        expr = "1" if i == 0 else f"cf.d{i-1} + 0"
        resp = await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={
                "name": key,
                "type": "formula",
                "key": key,
                "formulaExpr": expr,
                "formulaResultType": "number",
            },
        )
        if i < 8:
            assert resp.status_code == 200, (i, resp.text)
            prev = resp.json()["data"]["id"]
        else:
            # depth of d8 depending on d0..d7 chain is 8 edges? 
            # depth = longest path of formula deps. d0 depth0; d1 depth1; ... d8 depth8 → reject if >8
            # design: depth ≤ 8. So d8 (depth 8) should still OK; d9 depth 9 reject.
            assert resp.status_code == 200, (i, resp.text)

    # d9 → depth 9
    resp = await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "d9",
            "type": "formula",
            "key": "d9",
            "formulaExpr": "cf.d8 + 0",
            "formulaResultType": "number",
        },
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_upsert_formula_value_rejected(test_client: AsyncClient):
    user = await _register(test_client, "e40_ro")
    h = _auth(user["token"], user["workspaceId"])
    f = await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "Const",
            "type": "formula",
            "key": "const",
            "formulaExpr": "42",
            "formulaResultType": "number",
        },
    )
    assert f.status_code == 200, f.text
    issue = await _create_issue(test_client, user)
    resp = await test_client.patch(
        f"/api/issues/{issue['id']}/custom-fields",
        headers=h,
        json={"values": [{"key": "const", "value": 99}]},
    )
    assert resp.status_code == 400
    assert "只读" in resp.text or "公式" in resp.text


@pytest.mark.asyncio
async def test_eval_if_coalesce_and_div_zero(test_client: AsyncClient):
    user = await _register(test_client, "e40_ev")
    h = _auth(user["token"], user["workspaceId"])

    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={"name": "Weight", "type": "number", "key": "weight"},
    )
    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={"name": "Impact", "type": "number", "key": "impact"},
    )
    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "Score",
            "type": "formula",
            "key": "score",
            "formulaExpr": 'IF(issue.priority == "urgent", 10, COALESCE(cf.weight, 0) * COALESCE(cf.impact, 0))',
            "formulaResultType": "number",
        },
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

    issue = await _create_issue(test_client, user, priority="high")
    await test_client.patch(
        f"/api/issues/{issue['id']}/custom-fields",
        headers=h,
        json={"values": [{"key": "weight", "value": 3}, {"key": "impact", "value": 4}]},
    )

    detail = await test_client.get(
        f"/api/issues/{issue['id']}",
        headers=h,
    )
    assert detail.status_code == 200, detail.text
    cfs = {c["key"]: c for c in detail.json()["data"].get("customFields") or []}
    assert cfs["score"]["computed"] is True
    assert cfs["score"]["value"] == 12
    assert cfs["score"].get("error") in (None, "")

    # weight=0 → div_zero on ratio
    await test_client.patch(
        f"/api/issues/{issue['id']}/custom-fields",
        headers=h,
        json={"values": [{"key": "weight", "value": 0}]},
    )
    detail2 = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    cfs2 = {c["key"]: c for c in detail2.json()["data"].get("customFields") or []}
    assert cfs2["ratio"]["value"] is None
    assert cfs2["ratio"]["error"] == "div_zero"
    assert cfs2["score"]["value"] == 0  # COALESCE(0,0)*COALESCE(4,0)


@pytest.mark.asyncio
async def test_chained_formula_and_source_change(test_client: AsyncClient):
    user = await _register(test_client, "e40_ch")
    h = _auth(user["token"], user["workspaceId"])
    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={"name": "Base", "type": "number", "key": "base"},
    )
    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "Double",
            "type": "formula",
            "key": "double",
            "formulaExpr": "COALESCE(cf.base, 0) * 2",
            "formulaResultType": "number",
        },
    )
    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "Quad",
            "type": "formula",
            "key": "quad",
            "formulaExpr": "cf.double * 2",
            "formulaResultType": "number",
        },
    )
    issue = await _create_issue(test_client, user)
    await test_client.patch(
        f"/api/issues/{issue['id']}/custom-fields",
        headers=h,
        json={"values": [{"key": "base", "value": 5}]},
    )
    d1 = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    cfs = {c["key"]: c for c in d1.json()["data"]["customFields"]}
    assert cfs["double"]["value"] == 10
    assert cfs["quad"]["value"] == 20

    await test_client.patch(
        f"/api/issues/{issue['id']}/custom-fields",
        headers=h,
        json={"values": [{"key": "base", "value": 7}]},
    )
    d2 = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    cfs2 = {c["key"]: c for c in d2.json()["data"]["customFields"]}
    assert cfs2["quad"]["value"] == 28


@pytest.mark.asyncio
async def test_validate_formula_endpoint(test_client: AsyncClient):
    user = await _register(test_client, "e40_vf")
    h = _auth(user["token"], user["workspaceId"])
    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={"name": "Weight", "type": "number", "key": "weight"},
    )
    ok = await test_client.post(
        "/api/custom-fields/validate-formula",
        headers=h,
        json={"formulaExpr": "COALESCE(cf.weight, 0) + 1"},
    )
    assert ok.status_code == 200, ok.text
    data = ok.json()["data"]
    assert data["ok"] is True
    assert "cf.weight" in data["dependencies"]

    bad = await test_client.post(
        "/api/custom-fields/validate-formula",
        headers=h,
        json={"formulaExpr": "cf.missing + 1"},
    )
    assert bad.status_code == 200, bad.text
    assert bad.json()["data"]["ok"] is False


@pytest.mark.asyncio
async def test_viewer_reads_formula_writer_required_for_create(test_client: AsyncClient):
    owner = await _register(test_client, "e40_ow")
    viewer = await _register(test_client, "e40_vw")
    await _add_member(test_client, owner, viewer, role="viewer")
    oh = _auth(owner["token"], owner["workspaceId"])
    vh = _auth(viewer["token"], owner["workspaceId"])

    await test_client.post(
        "/api/custom-fields",
        headers=oh,
        json={
            "name": "Const",
            "type": "formula",
            "key": "const",
            "formulaExpr": "1 + 1",
            "formulaResultType": "number",
        },
    )
    issue = await _create_issue(test_client, owner)
    detail = await test_client.get(f"/api/issues/{issue['id']}", headers=vh)
    assert detail.status_code == 200
    cfs = {c["key"]: c for c in detail.json()["data"].get("customFields") or []}
    assert cfs["const"]["value"] == 2

    denied = await test_client.post(
        "/api/custom-fields",
        headers=vh,
        json={
            "name": "X",
            "type": "formula",
            "formulaExpr": "1",
            "formulaResultType": "number",
        },
    )
    assert denied.status_code == 403


@pytest.mark.asyncio
async def test_days_until_due_and_list_batch(test_client: AsyncClient):
    user = await _register(test_client, "e40_due")
    h = _auth(user["token"], user["workspaceId"])
    await test_client.post(
        "/api/custom-fields",
        headers=h,
        json={
            "name": "DaysLeft",
            "type": "formula",
            "key": "days_left",
            "formulaExpr": "days_until_due",
            "formulaResultType": "number",
        },
    )
    due = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%d")
    issue = await _create_issue(test_client, user, due_date=due)
    # also create another issue without due
    issue2 = await _create_issue(test_client, user, title="no-due")

    listed = await test_client.get("/api/issues", headers=h)
    assert listed.status_code == 200, listed.text
    rows = listed.json()["data"]["rows"] if "rows" in listed.json()["data"] else listed.json()["data"]
    # tolerate list shapes
    if isinstance(rows, dict):
        rows = rows.get("items") or rows.get("rows") or []
    by_id = {r["id"]: r for r in rows}
    if issue["id"] in by_id:
        cfs = {c["key"]: c for c in by_id[issue["id"]].get("customFields") or []}
        if "days_left" in cfs:
            assert cfs["days_left"]["value"] in (4, 5, 6)  # utc skew tolerance
    detail = await test_client.get(f"/api/issues/{issue['id']}", headers=h)
    cfs = {c["key"]: c for c in detail.json()["data"]["customFields"]}
    assert cfs["days_left"]["value"] in (4, 5, 6)
    detail2 = await test_client.get(f"/api/issues/{issue2['id']}", headers=h)
    cfs2 = {c["key"]: c for c in detail2.json()["data"]["customFields"]}
    assert cfs2["days_left"]["value"] is None


@pytest.mark.asyncio
async def test_illegal_ast_rejected(test_client: AsyncClient):
    user = await _register(test_client, "e40_ast")
    h = _auth(user["token"], user["workspaceId"])
    for expr in ["__import__('os')", "open('/etc/passwd')", "lambda x: x", "[x for x in [1]]"]:
        resp = await test_client.post(
            "/api/custom-fields",
            headers=h,
            json={
                "name": "Bad",
                "type": "formula",
                "key": f"bad_{uuid.uuid4().hex[:6]}",
                "formulaExpr": expr,
                "formulaResultType": "number",
            },
        )
        assert resp.status_code == 400, expr
