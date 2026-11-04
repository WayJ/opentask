"""Label (= Tag) commands (E14)."""
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


@click.group(name="label")
def label_cli():
    """标签 Labels（后端 /api/tags）。"""
    pass


@label_cli.command(name="list")
@click.option("--q", help="Search")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_list(obj, q, as_json):
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_tags(q=q))
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
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_create(obj, name, color, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.create_tag(name=name, color=color))
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


@label_cli.command(name="attach")
@click.argument("issue_ref")
@click.argument("tag_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_attach(obj, issue_ref, tag_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        async def run():
            iid = await _resolve_issue_id(client, issue_ref)
            return await client.attach_issue_tag(iid, tag_id)
        data = asyncio.run(run())
        if json_mode:
            echo_json(True, data=data, message="attached")
            return
        obj.skin.success("已挂标签")
    except APIError as e:
        handle_api_error(e, json_mode)


@label_cli.command(name="detach")
@click.argument("issue_ref")
@click.argument("tag_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def label_detach(obj, issue_ref, tag_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        async def run():
            iid = await _resolve_issue_id(client, issue_ref)
            return await client.detach_issue_tag(iid, tag_id)
        data = asyncio.run(run())
        if json_mode:
            echo_json(True, data=data, message="detached")
            return
        obj.skin.success("已摘标签")
    except APIError as e:
        handle_api_error(e, json_mode)
