"""Workspace commands (E14) — list / use / current / show."""
from __future__ import annotations

import asyncio
import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, unwrap_rows
from ..utils.config import Config
from ..utils.repl_skin import ReplSkin


@click.group(name="workspace")
def workspace_cli():
    """工作区：切换上下文（请求头 X-Workspace-Id）。"""
    pass


@workspace_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def workspace_list(obj, as_json: bool):
    """列出当前用户可访问的工作区。"""
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    client = make_client(config)

    try:
        rows = asyncio.run(client.list_workspaces())
        if not isinstance(rows, list):
            rows = unwrap_rows(rows)
        if json_mode:
            echo_json(True, data={"rows": rows, "total": len(rows)}, message="workspaces")
            return
        if not rows:
            skin.info("暂无工作区")
            return
        skin.section("Workspaces")
        active = config.active_workspace_id
        table = []
        for w in rows:
            wid = w.get("id", "")
            mark = "*" if wid == active else ""
            table.append([
                mark,
                wid[:8],
                w.get("name", ""),
                w.get("slug", "") or "",
                w.get("role", "") or "",
                w.get("issueKey", "") or "",
            ])
        skin.table(["", "ID", "Name", "Slug", "Role", "Key"], table)
        skin.hint("使用: opentask workspace use <id>")
    except APIError as e:
        handle_api_error(e, json_mode, "列出工作区失败")


@workspace_cli.command(name="use")
@click.argument("workspace_id")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def workspace_use(obj, workspace_id: str, as_json: bool):
    """设置当前工作区（持久化到 ~/.opentask/config.json）。"""
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    client = make_client(config)

    try:
        # Allow short prefix match against list
        rows = asyncio.run(client.list_workspaces())
        if not isinstance(rows, list):
            rows = unwrap_rows(rows)
        match = None
        for w in rows:
            wid = w.get("id", "")
            if wid == workspace_id or wid.startswith(workspace_id):
                match = w
                break
        if not match:
            # try get by id directly
            match = asyncio.run(client.get_workspace(workspace_id))
        wid = match.get("id", workspace_id)
        name = match.get("name", "")
        config.active_workspace_id = wid
        config.active_workspace_name = name
        if json_mode:
            echo_json(True, data={"id": wid, "name": name}, message=f"workspace={name}")
            return
        skin.success(f"当前工作区: {name} ({wid})")
    except APIError as e:
        handle_api_error(e, json_mode, "切换工作区失败")


@workspace_cli.command(name="current")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def workspace_current(obj, as_json: bool):
    """显示当前工作区。"""
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    wid = config.active_workspace_id
    name = config.active_workspace_name
    if not wid:
        if json_mode:
            echo_json(False, error="no active workspace", message="未选择工作区", status_code=400)
        else:
            skin.warning("未选择工作区。opentask workspace list && opentask workspace use <id>")
        return
    if json_mode:
        echo_json(True, data={"id": wid, "name": name}, message="current workspace")
        return
    skin.status_block({"ID": wid, "Name": name or "N/A"})


@workspace_cli.command(name="show")
@click.argument("workspace_id", required=False)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_obj
def workspace_show(obj, workspace_id: str | None, as_json: bool):
    """显示工作区详情（默认当前）。"""
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    wid = workspace_id or config.active_workspace_id
    if not wid:
        if json_mode:
            echo_json(False, error="no workspace", message="请指定 workspace_id 或先 use", status_code=400)
        else:
            skin.error("请指定 workspace_id 或先 workspace use")
        return
    client = make_client(config)
    try:
        data = asyncio.run(client.get_workspace(wid))
        if json_mode:
            echo_json(True, data=data, message="workspace")
            return
        skin.section("Workspace")
        skin.status_block({
            "ID": data.get("id", ""),
            "Name": data.get("name", ""),
            "Slug": data.get("slug", "") or "",
            "Role": data.get("role", "") or "",
            "Issue Key": data.get("issueKey", "") or "",
            "Cycles": "on" if data.get("cyclesEnabled") else "off",
        })
    except APIError as e:
        handle_api_error(e, json_mode, "获取工作区失败")
