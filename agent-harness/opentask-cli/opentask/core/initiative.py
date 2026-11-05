"""Initiative commands (E14)."""
from __future__ import annotations

import asyncio
import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="initiative")
def initiative_cli():
    """Initiatives（战略主题）。"""
    pass


@initiative_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def initiative_list(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_initiatives())
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("无 Initiative")
            return
        obj.skin.table(
            ["ID", "Name", "Status"],
            [[(r.get("id") or "")[:8], r.get("name") or "", r.get("status") or ""] for r in rows],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@initiative_cli.command(name="show")
@click.argument("initiative_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def initiative_show(obj, initiative_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_initiative(initiative_id))
        if json_mode:
            echo_json(True, data=data)
            return
        pids = data.get("projectIds") or []
        projs = data.get("projects") or []
        if isinstance(projs, list) and projs:
            projects_summary = ", ".join(
                [
                    (p.get("name") or p.get("id") or "")[:40]
                    for p in projs
                    if isinstance(p, dict)
                ]
            )
        else:
            projects_summary = ", ".join(str(x) for x in pids)
        obj.skin.status_block({
            "ID": data.get("id", ""),
            "Name": data.get("name", ""),
            "Status": data.get("status", ""),
            "Description": (data.get("description") or "")[:80],
            "Projects": projects_summary,
        })
    except APIError as e:
        handle_api_error(e, json_mode)


@initiative_cli.command(name="create")
@click.option("--name", "-n", required=True)
@click.option("--description", "-d", default=None)
@click.option("--status", default="active")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def initiative_create(obj, name, description, status, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        kwargs = {"status": status}
        if description is not None:
            kwargs["description"] = description
        data = asyncio.run(client.create_initiative(name, **kwargs))
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        obj.skin.success(f"已创建: {data.get('id', '')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@initiative_cli.command(name="update")
@click.argument("initiative_id")
@click.option("--name", "-n", default=None)
@click.option("--description", "-d", default=None)
@click.option("--status", default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def initiative_update(obj, initiative_id, name, description, status, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    body = {}
    if name is not None:
        body["name"] = name
    if description is not None:
        body["description"] = description
    if status is not None:
        body["status"] = status
    if not body:
        raise click.UsageError("至少提供一个更新字段")
    client = make_client(config)
    try:
        data = asyncio.run(client.update_initiative(initiative_id, **body))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success("已更新")
    except APIError as e:
        handle_api_error(e, json_mode)


@initiative_cli.command(name="delete")
@click.argument("initiative_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def initiative_delete(obj, initiative_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.delete_initiative(initiative_id))
        if json_mode:
            echo_json(True, data=data or {"id": initiative_id})
            return
        obj.skin.success("已删除")
    except APIError as e:
        handle_api_error(e, json_mode)


@initiative_cli.group(name="relations")
def relations_cli():
    """List Initiative relations."""
    pass


@relations_cli.command(name="list")
@click.argument("initiative_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def relations_list(obj, initiative_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_initiative_relations(initiative_id))
        if json_mode:
            echo_json(True, data=data)
            return
        items = (data or {}).get("items", []) if isinstance(data, dict) else []
        if not items:
            obj.skin.info("无关系")
            return
        obj.skin.table(
            ["ID", "Type", "Dir", "Peer"],
            [
                [
                    (i.get("id") or "")[:8],
                    i.get("type") or "",
                    i.get("direction") or "",
                    ((i.get("initiative") or {}).get("name") or "")[:40],
                ]
                for i in items
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@initiative_cli.group(name="relation")
def relation_cli():
    """Add / remove Initiative relations."""
    pass


@relation_cli.command(name="add")
@click.argument("initiative_id")
@click.option("--target", required=True, help="Target initiative id")
@click.option(
    "--type",
    "relation_type",
    required=True,
    type=click.Choice(["blocks", "is_blocked_by", "relates_to"], case_sensitive=True),
)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def relation_add(obj, initiative_id, target, relation_type, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(
            client.add_initiative_relation(initiative_id, target, relation_type)
        )
        if json_mode:
            echo_json(True, data=data, message="relation added")
            return
        obj.skin.success(f"已添加: {(data or {}).get('id', '')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@relation_cli.command(name="remove")
@click.argument("initiative_id")
@click.option("--relation-id", "relation_id", required=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def relation_remove(obj, initiative_id, relation_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(
            client.remove_initiative_relation(initiative_id, relation_id)
        )
        if json_mode:
            echo_json(True, data=data or {"id": relation_id}, message="relation removed")
            return
        obj.skin.success("已删除")
    except APIError as e:
        handle_api_error(e, json_mode)


def _parse_project_ids(ids_csv: str | None, positional: tuple[str, ...] | None) -> list[str]:
    """Parse --ids CSV and/or positional project ids (E90)."""
    ids: list[str] = []
    if ids_csv is not None:
        ids.extend([p.strip() for p in str(ids_csv).split(",") if p.strip()])
    for p in positional or ():
        s = str(p).strip()
        if s:
            ids.append(s)
    return ids


@initiative_cli.group(name="projects")
def projects_cli():
    """Set Initiative↔Projects association (full replace)."""
    pass


@projects_cli.command(name="set")
@click.argument("initiative_id")
@click.option(
    "--ids",
    "ids_csv",
    default=None,
    help="Comma-separated project ids (replace); empty clears",
)
@click.argument("positional_ids", nargs=-1)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def projects_set(obj, initiative_id, ids_csv, positional_ids, as_json):
    """E90: PUT /api/initiatives/{id}/projects — full replace (empty clears)."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    if ids_csv is None and not positional_ids:
        raise click.ClickException("Specify --ids ID1,ID2,... (empty clears) or positional project ids")
    project_ids = _parse_project_ids(ids_csv if ids_csv is not None else "", positional_ids)
    client = make_client(config)
    try:
        data = asyncio.run(client.set_initiative_projects(initiative_id, project_ids))
        if json_mode:
            echo_json(True, data=data, message="projects set")
            return
        pids = (data or {}).get("projectIds") if isinstance(data, dict) else None
        n = len(pids) if isinstance(pids, list) else len(project_ids)
        obj.skin.success(f"关联项目已更新（{n}）")
    except APIError as e:
        handle_api_error(e, json_mode)


@initiative_cli.group(name="project")
def project_cli():
    """Attach / detach a single Project to an Initiative."""
    pass


@project_cli.command(name="attach")
@click.argument("initiative_id")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def project_attach(obj, initiative_id, project_id, as_json):
    """E90: POST /api/initiatives/{id}/projects/{project_id}."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.attach_initiative_project(initiative_id, project_id))
        if json_mode:
            echo_json(True, data=data, message="project attached")
            return
        obj.skin.success(f"已关联项目: {project_id}")
    except APIError as e:
        handle_api_error(e, json_mode)


@project_cli.command(name="detach")
@click.argument("initiative_id")
@click.argument("project_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def project_detach(obj, initiative_id, project_id, as_json):
    """E90: DELETE /api/initiatives/{id}/projects/{project_id}."""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.detach_initiative_project(initiative_id, project_id))
        if json_mode:
            echo_json(True, data=data or {"id": initiative_id}, message="project detached")
            return
        obj.skin.success(f"已解除关联: {project_id}")
    except APIError as e:
        handle_api_error(e, json_mode)
