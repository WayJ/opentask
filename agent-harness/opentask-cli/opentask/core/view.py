"""Saved Views commands (E14) — list/show/use (read-oriented)."""
from __future__ import annotations

import asyncio
import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="view")
def view_cli():
    """Saved Views（只读 list/show/use）。"""
    pass


@view_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def view_list(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_saved_views())
        if json_mode:
            echo_json(True, data=data)
            return
        rows = data if isinstance(data, list) else (data or {}).get("rows", [])
        if not rows:
            obj.skin.info("无 Saved View")
            return
        obj.skin.table(
            ["ID", "Name", "Shared"],
            [[(r.get("id") or "")[:8], r.get("name") or "", str(r.get("isShared") or r.get("shared") or "")] for r in rows],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@view_cli.command(name="show")
@click.argument("view_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def view_show(obj, view_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_saved_view(view_id))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.status_block({
            "ID": data.get("id", ""),
            "Name": data.get("name", ""),
            "Filters": str(data.get("filters") or data.get("filter") or "")[:120],
        })
    except APIError as e:
        handle_api_error(e, json_mode)


@view_cli.command(name="use")
@click.argument("view_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def view_use(obj, view_id, as_json):
    """打印视图 filter JSON，供 agent 后续拼 issue list 参数。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_saved_view(view_id))
        filters = data.get("filters") if isinstance(data, dict) else None
        if filters is None and isinstance(data, dict):
            filters = data.get("filter") or data
        payload = {"viewId": view_id, "name": (data or {}).get("name"), "filters": filters}
        # always JSON-ish for agent consumption
        echo_json(True, data=payload, message="use this filter with issue list")
    except APIError as e:
        handle_api_error(e, json_mode)
