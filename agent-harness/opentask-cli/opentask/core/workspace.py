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
        bh = data.get("businessHours") or {}
        skin.status_block({
            "ID": data.get("id", ""),
            "Name": data.get("name", ""),
            "Slug": data.get("slug", "") or "",
            "Role": data.get("role", "") or "",
            "Issue Key": data.get("issueKey", "") or "",
            "Cycles": "on" if data.get("cyclesEnabled") else "off",
            "Timezone": data.get("timezone") or "—",
            "BusinessHours": "on" if bh.get("enabled") else "off",
        })
    except APIError as e:
        handle_api_error(e, json_mode, "获取工作区失败")


@workspace_cli.command(name="update")
@click.option("--timezone", default=None, help="IANA timezone (e.g. Asia/Shanghai)")
@click.option("--business-hours-enabled/--no-business-hours-enabled", default=None)
@click.option("--business-hours-json", default=None, help='JSON: {"enabled":true,"windows":{...}}')
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def workspace_update(obj, timezone, business_hours_enabled, business_hours_json, as_json):
    """更新工作区（E50: timezone / business hours）。需当前 workspace use。"""
    import json as _json
    config: Config = obj.config
    skin: ReplSkin = obj.skin
    json_mode = as_json or obj.json_mode
    wid = config.active_workspace_id
    if not wid:
        if json_mode:
            echo_json(False, error="no workspace", message="先 workspace use", status_code=400)
        else:
            skin.error("请先 workspace use")
        return
    body = {}
    if timezone is not None:
        body["timezone"] = timezone
    if business_hours_enabled is not None or business_hours_json is not None:
        bh = {}
        if business_hours_json:
            bh = _json.loads(business_hours_json)
        if business_hours_enabled is not None:
            bh["enabled"] = bool(business_hours_enabled)
        body["businessHours"] = bh
    if not body:
        if json_mode:
            echo_json(False, error="empty", message="无更新字段", status_code=400)
        else:
            skin.warning("无更新字段")
        return
    client = make_client(config)
    try:
        data = asyncio.run(client.update_workspace(wid, **body))
        if json_mode:
            echo_json(True, data=data, message="workspace updated")
            return
        skin.success("工作区已更新")
        bh = (data or {}).get("businessHours") or {}
        skin.status_block({
            "Timezone": (data or {}).get("timezone") or "—",
            "BusinessHours": "on" if bh.get("enabled") else "off",
        })
    except APIError as e:
        handle_api_error(e, json_mode, "更新工作区失败")
