"""Inbox + snooze commands (E14)."""
from __future__ import annotations

import asyncio
import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client
from ..utils.config import Config


@click.group(name="inbox")
def inbox_cli():
    """收件箱 Inbox（可带当前 workspace 过滤）。"""
    pass


@inbox_cli.command(name="list")
@click.option("--unread-only", is_flag=True)
@click.option("--include-snoozed", is_flag=True)
@click.option("--page", default=1)
@click.option("--page-size", default=20)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def inbox_list(obj, unread_only, include_snoozed, page, page_size, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    client = make_client(config)
    try:
        data = asyncio.run(client.list_inbox(
            unread_only=unread_only, include_snoozed=include_snoozed, page=page, page_size=page_size
        ))
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        unread = (data or {}).get("unreadCount", 0) if isinstance(data, dict) else 0
        obj.skin.section(f"Inbox (unread={unread})")
        if not rows:
            obj.skin.info("无通知")
            return
        obj.skin.table(
            ["ID", "Type", "Title", "Read"],
            [[
                (r.get("id") or "")[:8],
                r.get("type") or r.get("kind") or "",
                (r.get("title") or r.get("body") or "")[:40],
                "Y" if r.get("readAt") or r.get("isRead") else "N",
            ] for r in rows],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@inbox_cli.command(name="read")
@click.argument("notification_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def inbox_read(obj, notification_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    client = make_client(config)
    try:
        data = asyncio.run(client.inbox_read(notification_id))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success("已读")
    except APIError as e:
        handle_api_error(e, json_mode)


@inbox_cli.command(name="read-all")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def inbox_read_all(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    client = make_client(config)
    try:
        data = asyncio.run(client.inbox_read_all())
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success(f"已全部标记已读: {data.get('updated', '')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@inbox_cli.command(name="snooze")
@click.argument("notification_id")
@click.option("--until", required=True, help="ISO datetime")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def inbox_snooze(obj, notification_id, until, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    client = make_client(config)
    try:
        data = asyncio.run(client.inbox_snooze(notification_id, until))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success("已延后")
    except APIError as e:
        handle_api_error(e, json_mode)


@inbox_cli.command(name="unsnooze")
@click.argument("notification_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def inbox_unsnooze(obj, notification_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    client = make_client(config)
    try:
        data = asyncio.run(client.inbox_unsnooze(notification_id))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success("已取消延后")
    except APIError as e:
        handle_api_error(e, json_mode)
