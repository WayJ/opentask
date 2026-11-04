"""Favorites commands (E14)."""
from __future__ import annotations

import asyncio
import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="favorite")
def favorite_cli():
    """侧栏收藏 Favorites。"""
    pass


@favorite_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def favorite_list(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_favorites())
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("无收藏")
            return
        obj.skin.table(
            ["ID", "Type", "Target"],
            [[(r.get("id") or "")[:8], r.get("targetType") or r.get("target_type") or "", r.get("targetId") or r.get("target_id") or ""] for r in rows],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@favorite_cli.command(name="add")
@click.option("--type", "target_type", required=True, help="issue|project|…")
@click.option("--id", "target_id", required=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def favorite_add(obj, target_type, target_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.add_favorite(target_type, target_id))
        if json_mode:
            echo_json(True, data=data, message="favorited")
            return
        obj.skin.success("已收藏")
    except APIError as e:
        handle_api_error(e, json_mode)


@favorite_cli.command(name="remove")
@click.argument("favorite_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def favorite_remove(obj, favorite_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.remove_favorite(favorite_id))
        if json_mode:
            echo_json(True, data=data or {"id": favorite_id})
            return
        obj.skin.success("已移除收藏")
    except APIError as e:
        handle_api_error(e, json_mode)
