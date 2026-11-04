"""Custom field commands (E25)."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="custom-field")
def custom_field_cli():
    """Workspace Issue 自定义字段。"""
    pass


@custom_field_cli.command(name="list")
@click.option("--include-archived", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def custom_field_list(obj, include_archived, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_custom_fields(include_archived=include_archived))
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("无自定义字段")
            return
        obj.skin.table(
            ["Key", "Name", "Type", "Pos", "Archived"],
            [
                [
                    r.get("key") or "",
                    r.get("name") or "",
                    r.get("type") or "",
                    str(r.get("position") if r.get("position") is not None else ""),
                    "yes" if r.get("archivedAt") else "",
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@custom_field_cli.command(name="create")
@click.option("--name", "-n", required=True)
@click.option(
    "--type",
    "field_type",
    required=True,
    type=click.Choice(
        ["text", "number", "single_select", "multi_select", "date", "boolean"],
        case_sensitive=False,
    ),
)
@click.option("--key", "key", default=None, help="slug；默认从 name 生成")
@click.option(
    "--option",
    "-o",
    multiple=True,
    help="select 选项；可重复，或 value=label",
)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def custom_field_create(obj, name, field_type, key, option, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    kwargs = {}
    if key:
        kwargs["key"] = key
    if option:
        opts = []
        for raw in option:
            if "=" in raw:
                value, label = raw.split("=", 1)
                opts.append({"value": value.strip(), "label": label.strip() or value.strip()})
            else:
                opts.append(raw.strip())
        kwargs["options"] = opts
    try:
        data = asyncio.run(client.create_custom_field(name, field_type, **kwargs))
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        obj.skin.success(f"已创建字段: {data.get('key')} ({data.get('id', '')[:8]})")
    except APIError as e:
        handle_api_error(e, json_mode)
