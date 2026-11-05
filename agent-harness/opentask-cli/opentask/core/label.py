"""Label (= Tag) commands (E14 / E86 set·update·multi / E87 tag-group)."""
from __future__ import annotations

import asyncio
import re
import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config
from ..utils.repl_skin import ReplSkin

_CODE = re.compile(r"^(?:ISSUE\d+|[A-Za-z][A-Za-z0-9]{0,5})-\d+$", re.I)


async def _resolve_issue_id(client, issue_ref: str) -> str:
    if _CODE.match(issue_ref):
        info = await client.get_issue(issue_ref, by_code=True)
        return info.get("id", issue_ref)
    return issue_ref


def _collect_tag_ids(positional: str | None, tag_ids_opt: tuple[str, ...]) -> list[str]:
    ids: list[str] = []
    if positional:
        ids.append(str(positional))
    for t in tag_ids_opt:
        if t is not None and str(t) != "":
            ids.append(str(t))
    # de-dupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def _parse_ids_csv(ids: str | None) -> list[int]:
    if ids is None or ids.strip() == "":
        return []
    parts = [p.strip() for p in ids.split(",")]
    out: list[int] = []
    for p in parts:
        if not p:
            continue
        out.append(int(p))
    return out


@click.group(name="label")
def label_cli():
    """标签 Labels（后端 /api/tags）。"""
    pass


@label_cli.command(name="list")
@click.option("--group-id", default=None, help="Filter by tag group UUID")
@click.option("--q", help="Search")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_list(obj, group_id, q, as_json):
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_tags(group_id=group_id, q=q))
        rows = data.get("rows", []) if isinstance(data, dict) else data
        if json_mode:
            echo_json(True, data={"rows": rows, "total": len(rows) if isinstance(rows, list) else 0})
            return
        if not rows:
            skin.info("暂无标签")
            return
        skin.table(
            ["ID", "Name", "Color"],
            [[str(r.get("id", "")), r.get("name", ""), r.get("color") or ""] for r in rows],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@label_cli.command(name="create")
@click.option("--name", "-n", required=True)
@click.option("--color", "-c", default=None)
@click.option("--group-id", default=None, help="Tag group UUID")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_create(obj, name, color, group_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.create_tag(name=name, color=color, group_id=group_id))
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        obj.skin.success(f"标签已创建: {data.get('name', name)}")
    except APIError as e:
        handle_api_error(e, json_mode)


@label_cli.command(name="delete")
@click.argument("tag_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_delete(obj, tag_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.delete_tag(tag_id))
        if json_mode:
            echo_json(True, data=data or {"id": tag_id}, message="deleted")
            return
        obj.skin.success("标签已删除")
    except APIError as e:
        handle_api_error(e, json_mode)


@label_cli.command(name="set")
@click.argument("issue_ref")
@click.option("--ids", default=None, help="Comma-separated tag ids (replace); empty clears")
@click.option("--clear", is_flag=True, default=False, help="Clear all tags (PUT tag_ids=[])")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_set(obj, issue_ref, ids, clear, as_json):
    """E86: replace Issue tags (PUT /api/issues/{id}/tags)."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    if not clear and ids is None:
        msg = "Specify --ids or --clear"
        if json_mode:
            echo_json(False, message=msg)
        else:
            skin.error(msg)
        raise SystemExit(1)
    tag_ids = [] if clear else _parse_ids_csv(ids)
    client = make_client(config)
    try:
        async def run():
            iid = await _resolve_issue_id(client, issue_ref)
            return await client.replace_issue_tags(iid, tag_ids)

        data = asyncio.run(run())
        if json_mode:
            echo_json(True, data=data, message="set")
            return
        total = data.get("total") if isinstance(data, dict) else None
        skin.success(f"标签已替换（{total if total is not None else len(tag_ids)}）")
    except APIError as e:
        handle_api_error(e, json_mode)
    except ValueError as e:
        if json_mode:
            echo_json(False, message=str(e))
        else:
            skin.error(str(e))
        raise SystemExit(1)


@label_cli.command(name="update")
@click.argument("tag_id")
@click.option("--name", default=None, help="New tag name")
@click.option("--color", default=None, help="New tag color")
@click.option("--group-id", "group_id", type=str, default=None, help="Move to group (UUID)")
@click.option("--clear-group", is_flag=True, default=False, help="Clear group_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_update(obj, tag_id, name, color, group_id, clear_group, as_json):
    """E86: PATCH /api/tags/{id}."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    if name is None and color is None and group_id is None and not clear_group:
        msg = "Specify at least one of --name/--color/--group-id/--clear-group"
        if json_mode:
            echo_json(False, message=msg)
        else:
            skin.error(msg)
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(
            client.update_tag(
                tag_id,
                name=name,
                color=color,
                group_id=group_id,
                clear_group=clear_group,
            )
        )
        if json_mode:
            echo_json(True, data=data, message="updated")
            return
        skin.success(f"标签已更新: {data.get('name', tag_id) if isinstance(data, dict) else tag_id}")
    except APIError as e:
        handle_api_error(e, json_mode)


@label_cli.command(name="attach")
@click.argument("issue_ref")
@click.argument("tag_id", required=False, default=None)
@click.option("--tag-id", "tag_ids_opt", multiple=True, help="Tag id (repeatable)")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_attach(obj, issue_ref, tag_id, tag_ids_opt, as_json):
    """Attach one or more tags to an Issue (positional TAG or --tag-id)."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    ids = _collect_tag_ids(tag_id, tag_ids_opt)
    if not ids:
        msg = "Provide TAG positional or --tag-id"
        if json_mode:
            echo_json(False, message=msg)
        else:
            skin.error(msg)
        raise SystemExit(1)
    client = make_client(config)
    try:
        async def run():
            iid = await _resolve_issue_id(client, issue_ref)
            results = []
            for tid in ids:
                results.append(await client.attach_issue_tag(iid, tid))
            return results

        data = asyncio.run(run())
        if json_mode:
            echo_json(True, data=data if len(data) > 1 else data[0], message="attached")
            return
        skin.success(f"已挂标签（{len(ids)}）" if len(ids) > 1 else "已挂标签")
    except APIError as e:
        handle_api_error(e, json_mode)


@label_cli.command(name="detach")
@click.argument("issue_ref")
@click.argument("tag_id", required=False, default=None)
@click.option("--tag-id", "tag_ids_opt", multiple=True, help="Tag id (repeatable)")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_detach(obj, issue_ref, tag_id, tag_ids_opt, as_json):
    """Detach one or more tags from an Issue (positional TAG or --tag-id)."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    ids = _collect_tag_ids(tag_id, tag_ids_opt)
    if not ids:
        msg = "Provide TAG positional or --tag-id"
        if json_mode:
            echo_json(False, message=msg)
        else:
            skin.error(msg)
        raise SystemExit(1)
    client = make_client(config)
    try:
        async def run():
            iid = await _resolve_issue_id(client, issue_ref)
            results = []
            for tid in ids:
                results.append(await client.detach_issue_tag(iid, tid))
            return results

        data = asyncio.run(run())
        if json_mode:
            echo_json(True, data=data if len(data) > 1 else data[0], message="detached")
            return
        skin.success(f"已摘标签（{len(ids)}）" if len(ids) > 1 else "已摘标签")
    except APIError as e:
        handle_api_error(e, json_mode)


@label_cli.command(name="issue")
@click.argument("issue_ref")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_issue(obj, issue_ref, as_json):
    """E86: list tags on an Issue (GET /api/issues/{id}/tags)."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        async def run():
            iid = await _resolve_issue_id(client, issue_ref)
            return await client.list_issue_tags(iid)

        data = asyncio.run(run())
        rows = data.get("rows", []) if isinstance(data, dict) else data
        if json_mode:
            echo_json(
                True,
                data={"rows": rows, "total": len(rows) if isinstance(rows, list) else 0},
            )
            return
        if not rows:
            skin.info("该 Issue 暂无标签")
            return
        skin.table(
            ["ID", "Name", "Color"],
            [[str(r.get("id", "")), r.get("name", ""), r.get("color") or ""] for r in rows],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@label_cli.group(name="group")
def label_group_cli():
    """E87: label group list|create|update|delete."""
    pass


@label_group_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_group_list(obj, as_json):
    """E87: GET /api/tag-groups."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_tag_groups())
        rows = data.get("rows", []) if isinstance(data, dict) else data
        if json_mode:
            echo_json(True, data={"rows": rows, "total": len(rows) if isinstance(rows, list) else 0})
            return
        if not rows:
            skin.info("暂无标签组")
            return
        skin.table(
            ["ID", "Name", "Color", "Position"],
            [
                [
                    str(r.get("id", "")),
                    r.get("name", ""),
                    r.get("color") or "",
                    str(r.get("position", "")),
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@label_group_cli.command(name="create")
@click.option("--name", "-n", required=True)
@click.option("--color", "-c", default=None)
@click.option("--position", type=int, default=0)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_group_create(obj, name, color, position, as_json):
    """E87: POST /api/tag-groups."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.create_tag_group(name=name, color=color, position=position))
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        skin.success(f"标签组已创建: {data.get('name', name) if isinstance(data, dict) else name}")
    except APIError as e:
        handle_api_error(e, json_mode)


@label_group_cli.command(name="update")
@click.argument("group_id")
@click.option("--name", default=None)
@click.option("--color", default=None)
@click.option("--position", type=int, default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_group_update(obj, group_id, name, color, position, as_json):
    """E87: PATCH /api/tag-groups/{id}."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    if name is None and color is None and position is None:
        msg = "Specify at least one of --name/--color/--position"
        if json_mode:
            echo_json(False, message=msg)
        else:
            skin.error(msg)
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(
            client.update_tag_group(group_id, name=name, color=color, position=position)
        )
        if json_mode:
            echo_json(True, data=data, message="updated")
            return
        skin.success(
            f"标签组已更新: {data.get('name', group_id) if isinstance(data, dict) else group_id}"
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@label_group_cli.command(name="delete")
@click.argument("group_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_group_delete(obj, group_id, as_json):
    """E87: DELETE /api/tag-groups/{id}."""
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.delete_tag_group(group_id))
        if json_mode:
            echo_json(True, data=data or {"id": group_id}, message="deleted")
            return
        skin.success("标签组已删除")
    except APIError as e:
        handle_api_error(e, json_mode)
