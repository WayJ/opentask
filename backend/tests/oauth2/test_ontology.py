import json
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, select

from opentask.models.issue.model import Issue, IssueRelation, IssueTimeline
from opentask.models.user_center.model import Permission, RolePermission, UserRole
from opentask.models.requirement.model import Project
from opentask.models.workspace.model import Workspace, WorkspaceMember
from opentask.services.oauth2.client_service import OAuthClientService
from opentask.services.oauth2.token_service import OAuthTokenService
from .test_read_surface_scoping import _seed_department, _seed_role, _seed_member


@pytest_asyncio.fixture
async def ontology_graph(test_session):
    s = test_session
    suffix = uuid.uuid4().hex[:8]
    da = await _seed_department(s, "Ontology A " + suffix, "/ontology/" + suffix + "/a")
    db = await _seed_department(s, "Ontology B " + suffix, "/ontology/" + suffix + "/b")
    role = await _seed_role(s, "ontology_" + suffix)
    a = await _seed_member(s, role, da, "ont_a_" + suffix)
    b = await _seed_member(s, role, db, "ont_b_" + suffix)
    foreign_member = await _seed_member(s, role, da, "ont_f_" + suffix)
    inactive_member = await _seed_member(s, role, da, "ont_i_" + suffix)
    inactive_member.status = 0
    ws = Workspace(name="Ontology " + suffix, slug="ontology-" + suffix, issue_key="O" + suffix[:5].upper())
    other = Workspace(name="Other " + suffix, slug="other-" + suffix, issue_key="Z" + suffix[:5].upper())
    s.add_all([ws, other])
    await s.flush()
    s.add_all(
        [
            WorkspaceMember(workspace_id=ws.id, user_id=str(a.id)),
            WorkspaceMember(workspace_id=ws.id, user_id=str(b.id)),
            WorkspaceMember(workspace_id=other.id, user_id=str(foreign_member.id)),
            WorkspaceMember(workspace_id=ws.id, user_id=str(inactive_member.id)),
        ]
    )
    project = Project(name="Ontology project " + suffix, dept_id=str(da.id), workspace_id=ws.id)
    s.add(project)
    await s.flush()

    def issue(title, dept, owner, workspace, **extra):
        return Issue(
            issue_code="ONT-" + uuid.uuid4().hex[:12],
            title=title,
            type="bug",
            status="open",
            priority="high",
            dept_id=str(dept.id),
            reporter_id=str(owner.id),
            created_by=str(owner.id),
            workspace_id=workspace,
            **extra,
        )

    source = issue("Source " + suffix, da, a, ws.id, project_id=project.id, assignee_id=str(a.id))
    target = issue("Target " + suffix, da, a, ws.id)
    hidden = issue("Hidden " + suffix, db, b, ws.id)
    foreign = issue("Foreign " + suffix, da, a, other.id)
    gone = issue("Deleted " + suffix, da, a, ws.id, is_deleted=True)
    s.add_all([source, target, hidden, foreign, gone])
    await s.flush()
    s.add_all(
        [
            IssueRelation(source_id=source.id, target_id=x.id, relation_type="blocks")
            for x in [target, hidden, foreign, gone]
        ]
    )
    await s.commit()
    client, _ = await OAuthClientService(s).register(
        client_id="ont-" + suffix,
        name="Ontology",
        description=None,
        redirect_uris=["http://localhost/callback"],
        scopes=["read:tasks", "read:projects", "read:members", "profile"],
        created_by=str(a.id),
    )

    async def headers(scopes="read:tasks read:projects read:members profile", user=a):
        token = await OAuthTokenService(s).issue(user=user, client_id=client.client_id, scope=scopes)
        return {"Authorization": "Bearer " + token["access_token"]}

    yield dict(
        a=a,
        b=b,
        foreign_member=foreign_member,
        inactive_member=inactive_member,
        ws=ws,
        project=project,
        source=source,
        target=target,
        hidden=hidden,
        foreign=foreign,
        gone=gone,
        headers=headers,
        suffix=suffix,
    )
    ids = [x.id for x in [source, target, hidden, foreign, gone]]
    await s.execute(delete(IssueRelation).where(IssueRelation.source_id.in_(ids)))
    await s.execute(delete(Issue).where(Issue.id.in_(ids)))
    await s.execute(delete(Project).where(Project.id == project.id))
    await s.execute(delete(WorkspaceMember).where(WorkspaceMember.workspace_id.in_([ws.id, other.id])))
    await s.execute(delete(Workspace).where(Workspace.id.in_([ws.id, other.id])))
    await s.commit()


async def invoke(client, headers, name, args=None):
    return await client.post(
        "/mcp",
        headers=headers,
        json={"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": name, "arguments": args or {}}},
    )


def payload(response):
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert not result.get("isError", False), result
    data = json.loads(result["content"][0]["text"])
    assert result["structuredContent"] == data
    return data


def assert_tool_error(response, status):
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["isError"] is True
    assert result["structuredContent"]["error"]["status"] == status
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]


@pytest.mark.asyncio
async def test_ontology_discovery_describes_native_types_and_relations(test_client, ontology_graph):
    g = ontology_graph
    h = await g["headers"]()
    catalog = payload(await invoke(test_client, h, "discover_ontology"))
    assert catalog["version"] == "1.0.0"
    assert {x["name"] for x in catalog["object_types"]} == {"Issue", "Project", "Member"}
    schema = payload(await invoke(test_client, h, "describe_object_type", {"object_type": "Issue"}))
    assert schema["properties"]["status"]["enum"] == [
        "open",
        "in_progress",
        "feedback",
        "resolved",
        "closed",
        "rejected",
    ]
    assert "todo" not in schema["properties"]["status"]["enum"]
    relations = {x["name"]: x for x in schema["relations"]}
    assert relations["blocks"]["inverse"] == "is_blocked_by"
    assert relations["project"]["target_type"] == "Project"
    assert schema["actions"][0]["name"] == "update_issue_status"
    listing = await test_client.post("/mcp", headers=h, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    tool = next(x for x in listing.json()["result"]["tools"] if x["name"] == "search_objects")
    assert tool["inputSchema"]["additionalProperties"] is False
    assert tool["annotations"]["readOnlyHint"] is True


@pytest.mark.asyncio
async def test_objects_filter_before_count_and_paginate_stably(test_client, ontology_graph):
    g = ontology_graph
    h = await g["headers"]()
    args = {"object_type": "Issue", "query": g["suffix"], "limit": 1}
    first = payload(await invoke(test_client, h, "search_objects", args))
    assert first["total"] == 2 and first["has_more"] and first["next_offset"] == 1
    second = payload(await invoke(test_client, h, "search_objects", {**args, "offset": 1}))
    assert {first["items"][0]["id"], second["items"][0]["id"]} == {g["source"].id, g["target"].id}
    assert second["has_more"] is False and second["next_offset"] is None
    found = payload(
        await invoke(
            test_client,
            h,
            "search_objects",
            {"object_type": "Issue", "filters": {"project_id": g["project"].id, "status": "open"}},
        )
    )
    assert [x["id"] for x in found["items"]] == [g["source"].id]
    obj = payload(await invoke(test_client, h, "get_object", {"object_type": "Issue", "object_id": g["source"].id}))
    assert obj["properties"]["status"] == "open"
    for key in ["hidden", "foreign", "gone"]:
        r = await invoke(test_client, h, "get_object", {"object_type": "Issue", "object_id": g[key].id})
        assert_tool_error(r, 404)


@pytest.mark.asyncio
async def test_relations_check_both_ends_and_resolve_inverse(test_client, ontology_graph):
    g = ontology_graph
    h = await g["headers"]()
    related = payload(
        await invoke(
            test_client,
            h,
            "get_related_objects",
            {"object_type": "Issue", "object_id": g["source"].id, "relation": "blocks"},
        )
    )
    assert related["total"] == 1 and [x["id"] for x in related["items"]] == [g["target"].id]
    inverse = payload(
        await invoke(
            test_client,
            h,
            "get_related_objects",
            {"object_type": "Issue", "object_id": g["target"].id, "relation": "is_blocked_by"},
        )
    )
    assert [x["id"] for x in inverse["items"]] == [g["source"].id]
    project = payload(
        await invoke(
            test_client,
            h,
            "get_related_objects",
            {"object_type": "Issue", "object_id": g["source"].id, "relation": "project"},
        )
    )
    assert project["items"][0]["id"] == g["project"].id
    project_issues = payload(
        await invoke(
            test_client,
            h,
            "get_related_objects",
            {"object_type": "Project", "object_id": g["project"].id, "relation": "issues"},
        )
    )
    assert [x["id"] for x in project_issues["items"]] == [g["source"].id]
    hidden = await invoke(
        test_client,
        h,
        "get_related_objects",
        {"object_type": "Issue", "object_id": g["hidden"].id, "relation": "blocks"},
    )
    assert_tool_error(hidden, 404)


@pytest.mark.asyncio
async def test_scopes_member_visibility_and_safe_projection(test_client, ontology_graph):
    g = ontology_graph
    h = await g["headers"]("read:tasks profile")
    # A visible issue does not confer permission to its project or the member directory.
    r = await invoke(
        test_client,
        h,
        "get_related_objects",
        {"object_type": "Issue", "object_id": g["source"].id, "relation": "project"},
    )
    assert_tool_error(r, 403)
    own = payload(await invoke(test_client, h, "search_objects", {"object_type": "Member"}))
    assert [x["id"] for x in own["items"]] == [str(g["a"].id)]
    assert set(own["items"][0]["properties"]) == {"username", "name"}
    all_visible = payload(
        await invoke(test_client, await g["headers"]("read:members"), "search_objects", {"object_type": "Member"})
    )
    assert [item["id"] for item in all_visible["items"]] == [str(g["a"].id)]
    for key in ("foreign_member", "inactive_member"):
        assert_tool_error(
            await invoke(
                test_client,
                await g["headers"]("read:members"),
                "get_object",
                {"object_type": "Member", "object_id": str(g[key].id)},
            ),
            404,
        )

    assert_tool_error(
        await invoke(test_client, h, "get_object", {"object_type": "Member", "object_id": str(g["b"].id)}), 404
    )
    assert_tool_error(
        await invoke(
            test_client,
            await g["headers"]("read:members"),
            "get_object",
            {"object_type": "Member", "object_id": str(g["b"].id)},
        ),
        404,
    )
    no_tasks = await g["headers"]("profile")
    assert_tool_error(await invoke(test_client, no_tasks, "search_objects", {"object_type": "Issue"}), 403)
    assert (await invoke(test_client, no_tasks, "discover_ontology")).status_code == 200


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "args",
    [
        {"object_type": "Issue", "limit": True},
        {"object_type": "Unknown"},
        {"object_type": "Issue", "filters": {"status": "todo"}},
        {"object_type": "Project", "filters": {"assignee_id": "someone"}},
        {"object_type": "Issue", "extra": "ignored"},
        {"object_type": "Issue", "offset": -1},
    ],
)
async def test_ontology_rejects_invalid_query(test_client, ontology_graph, args):
    assert_tool_error(await invoke(test_client, await ontology_graph["headers"](), "search_objects", args), 400)


@pytest.mark.asyncio
async def test_mcp_protocol_errors_do_not_crash(test_client, ontology_graph):
    h = await ontology_graph["headers"]()
    for value in [
        [],
        None,
        {"jsonrpc": "1.0", "id": 1, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": None},
    ]:
        r = await test_client.post("/mcp", headers={**h, "Content-Type": "application/json"}, content=json.dumps(value))
        assert r.status_code == 200 and r.json()["error"]["code"] == -32600
    r = await test_client.post("/mcp", headers={**h, "Content-Type": "application/json"}, content="{")
    assert r.json()["error"]["code"] == -32700
    unknown = await invoke(test_client, h, "does_not_exist")
    assert unknown.json()["error"]["code"] == -32602


@pytest.mark.asyncio
async def test_relation_hides_invisible_project_and_disabled_caller(test_client, test_session, ontology_graph):
    g = ontology_graph
    h = await g["headers"]()
    g["project"].dept_id = None
    await test_session.commit()
    related = payload(
        await invoke(
            test_client,
            h,
            "get_related_objects",
            {"object_type": "Issue", "object_id": g["source"].id, "relation": "project"},
        )
    )
    assert related["items"] == [] and related["total"] == 0
    obj = payload(await invoke(test_client, h, "get_object", {"object_type": "Issue", "object_id": g["source"].id}))
    assert "project_id" not in obj["properties"]
    g["a"].status = 0
    await test_session.commit()
    assert (await invoke(test_client, h, "discover_ontology")).status_code == 401


@pytest.mark.asyncio
async def test_description_output_is_bounded_with_explicit_truncation(test_client, test_session, ontology_graph):
    g = ontology_graph
    h = await g["headers"]()
    g["source"].description = "测" * 9000
    await test_session.commit()
    obj = payload(await invoke(test_client, h, "get_object", {"object_type": "Issue", "object_id": g["source"].id}))
    assert len(obj["properties"]["description"]) == 8000 and obj["truncated_properties"] == ["description"]
    result = payload(
        await invoke(
            test_client, h, "search_objects", {"object_type": "Issue", "filters": {"project_id": g["project"].id}}
        )
    )
    assert len(result["items"][0]["properties"]["description"]) == 1000
    assert result["items"][0]["truncated_properties"] == ["description"]


@pytest.mark.asyncio
async def test_status_action_enforces_scope_permissions_visibility_and_records_change(test_client, test_session, ontology_graph):
    g = ontology_graph
    args = {"object_id": g["source"].id, "status": "resolved"}
    read = await g["headers"]()
    write = await g["headers"]("read:tasks write:tasks")
    assert_tool_error(await invoke(test_client, read, "update_issue_status", args), 403)
    assert_tool_error(await invoke(test_client, write, "update_issue_status", args), 403)
    role_id = (await test_session.execute(select(UserRole.role_id).where(UserRole.user_id == str(g["a"].id)))).scalar_one()
    perm = (await test_session.execute(select(Permission).where(Permission.code == "issue:update"))).scalar_one_or_none()
    if not perm:
        perm = Permission(code="issue:update", name="编辑Issue", type="button", status=1)
        test_session.add(perm)
        await test_session.flush()
    test_session.add(RolePermission(role_id=role_id, permission_id=str(perm.id)))
    membership = (await test_session.execute(select(WorkspaceMember).where(WorkspaceMember.workspace_id == g["ws"].id, WorkspaceMember.user_id == str(g["a"].id)))).scalar_one()
    membership.role = "viewer"
    await test_session.commit()
    assert_tool_error(await invoke(test_client, write, "update_issue_status", args), 403)
    membership.role = "member"
    await test_session.commit()
    for key in ("hidden", "foreign", "gone"):
        assert_tool_error(await invoke(test_client, write, "update_issue_status", {**args, "object_id": g[key].id}), 404)
    assert_tool_error(await invoke(test_client, write, "update_issue_status", {**args, "status": "done"}), 400)
    result = payload(await invoke(test_client, write, "update_issue_status", args))
    assert (result["previous_status"], result["status"], result["changed"]) == ("open", "resolved", True)
    again = payload(await invoke(test_client, write, "update_issue_status", args))
    assert again["changed"] is False
    timeline = (await test_session.execute(select(IssueTimeline).where(IssueTimeline.issue_id == g["source"].id, IssueTimeline.action_type == "status_changed"))).scalars().all()
    assert len(timeline) == 1 and timeline[0].user_id == str(g["a"].id)
    assert timeline[0].action_data == {"from": "open", "to": "resolved"}
    obj = payload(await invoke(test_client, write, "get_object", {"object_type": "Issue", "object_id": g["source"].id}))
    assert obj["properties"]["status"] == "resolved"
    listing = await test_client.post("/mcp", headers=write, json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    action = next(x for x in listing.json()["result"]["tools"] if x["name"] == "update_issue_status")
    assert action["annotations"]["readOnlyHint"] is False


@pytest.mark.asyncio
async def test_object_set_projection_filter_sort_aggregate_and_action_schema(test_client, ontology_graph):
    g = ontology_graph
    h = await g["headers"]()
    args = {"object_type": "Issue", "select": ["issue_code", "status"], "where": [{"field": "status", "op": "in", "values": ["open", "resolved"]}], "order_by": {"field": "issue_code", "direction": "asc"}, "limit": 1}
    result = payload(await invoke(test_client, h, "query_object_set", args))
    assert result["total"] == 2 and result["has_more"]
    assert set(result["items"][0]["properties"]) == {"issue_code", "status"}
    count = payload(await invoke(test_client, h, "query_object_set", {"object_type": "Issue", "aggregate": {"group_by": "status"}}))
    assert count["groups"] == [{"value": "open", "count": 2}]
    action = payload(await invoke(test_client, h, "describe_action", {"action": "update_issue_status"}))
    assert action["input_schema"]["properties"]["status"]["enum"]
    assert action["required_scopes"] == ["read:tasks", "write:tasks"]
    for bad in [{"object_type": "Issue", "select": ["password_hash"]}, {"object_type": "Issue", "where": [{"field": "status", "op": "eq", "values": ["bogus"]}]}, {"object_type": "Issue", "order_by": {"field": "password_hash", "direction": "asc"}}]:
        assert_tool_error(await invoke(test_client, h, "query_object_set", bad), 400)


@pytest.mark.asyncio
async def test_object_set_relation_requires_visible_targets_and_both_scopes(test_client, ontology_graph):
    g = ontology_graph
    args = {"object_type": "Issue", "related": {"relation": "blocks", "where": [{"field": "title", "op": "eq", "values": ["Target " + g["suffix"]]}]}}
    result = payload(await invoke(test_client, await g["headers"](), "query_object_set", args))
    assert result["total"] == 1 and result["items"][0]["id"] == g["source"].id
    args["related"]["where"][0]["values"] = ["Hidden " + g["suffix"]]
    result = payload(await invoke(test_client, await g["headers"](), "query_object_set", args))
    assert result["total"] == 0
    relation = {"object_type": "Issue", "related": {"relation": "project", "where": [{"field": "name", "op": "eq", "values": [g["project"].name]}]}}
    assert_tool_error(await invoke(test_client, await g["headers"]("read:tasks"), "query_object_set", relation), 403)
