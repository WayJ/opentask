"""Display prefs commands (E93)."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="display-prefs")
def display_prefs_cli():
    """个人 Issue 列表·看板 Display prefs。"""
    pass


def _parse_display_json(raw: str) -> dict:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"JSON 无效: {e}") from e
    if not isinstance(parsed, dict):
        raise click.ClickException("--display 必须是 JSON 对象")
    return parsed


def _human_summary(skin, payload: dict | None) -> None:
    display = None
    if isinstance(payload, dict):
        display = payload.get("display")
    if display is None:
        skin.info("无 Display prefs（display: null）")
        return
    if not isinstance(display, dict):
        skin.info(f"display: {display}")
        return
    skin.section("Issue Display prefs")
    skin.table(
        ["Key", "Value"],
        [
            ["View mode", display.get("view_mode", "")],
            ["Group by", display.get("group_by", "")],
            ["Swimlane by", display.get("swimlane_by", "")],
            ["Hide empty lanes", display.get("hide_empty_lanes", "")],
        ],
    )


@display_prefs_cli.command(name="get")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def display_prefs_get(obj, as_json):
    """读取当前用户 × workspace 的 Issue Display prefs。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_issue_display_prefs())
        if json_mode:
            echo_json(True, data=data)
            return
        _human_summary(obj.skin, data if isinstance(data, dict) else None)
    except APIError as e:
        handle_api_error(e, json_mode)


@display_prefs_cli.command(name="set")
@click.option("--display", "display_json", required=True, help="Display JSON object (snake_case keys)")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def display_prefs_set(obj, display_json, as_json):
    """写入当前用户 × workspace 的 Issue Display prefs（PUT upsert）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    display = _parse_display_json(display_json)
    client = make_client(config)
    try:
        data = asyncio.run(client.put_issue_display_prefs(display))
        if json_mode:
            echo_json(True, data=data, message="saved")
            return
        obj.skin.success("Display prefs 已保存")
        _human_summary(obj.skin, data if isinstance(data, dict) else {"display": display})
    except APIError as e:
        handle_api_error(e, json_mode)
