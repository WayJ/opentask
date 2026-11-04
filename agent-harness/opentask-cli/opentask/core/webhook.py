"""Outbound webhook commands (E29)."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config

EVENTS = [
    "issue.created",
    "issue.updated",
    "issue.status_changed",
    "comment.created",
    "issue.custom_field_changed",
]


@click.group(name="webhook")
def webhook_cli():
    """工作区出站 Webhook。"""
    pass


@webhook_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_list(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_webhooks())
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("无 Webhook")
            return
        obj.skin.table(
            ["Name", "URL", "Events", "Enabled", "Id"],
            [
                [
                    r.get("name") or "",
                    (r.get("url") or "")[:48],
                    ",".join(r.get("events") or []),
                    "yes" if r.get("enabled") else "no",
                    (r.get("id") or "")[:8],
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@webhook_cli.command(name="create")
@click.option("--url", "-u", required=True)
@click.option(
    "--events",
    "-e",
    required=True,
    help="逗号分隔事件，如 issue.created,issue.updated",
)
@click.option("--name", "-n", default=None)
@click.option("--disabled", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_create(obj, url, events, name, disabled, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    ev_list = [x.strip() for x in events.split(",") if x.strip()]
    for ev in ev_list:
        if ev not in EVENTS:
            raise click.ClickException(f"未知事件: {ev}；允许: {', '.join(EVENTS)}")
    client = make_client(config)
    try:
        data = asyncio.run(
            client.create_webhook(url, ev_list, name=name, enabled=not disabled)
        )
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        secret = (data or {}).get("secret")
        obj.skin.success(
            f"已创建: {(data.get('id') or '')[:8]} url={data.get('url')}"
        )
        if secret:
            obj.skin.warning(f"Signing secret（仅此一次）: {secret}")
    except APIError as e:
        handle_api_error(e, json_mode)


@webhook_cli.command(name="update")
@click.argument("webhook_id")
@click.option("--url", default=None)
@click.option("--events", default=None, help="逗号分隔；省略则不改")
@click.option("--name", default=None)
@click.option("--enabled", type=click.BOOL, default=None, help="true/false")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_update(obj, webhook_id, url, events, name, enabled, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    body = {}
    if url is not None:
        body["url"] = url
    if events is not None:
        body["events"] = [x.strip() for x in events.split(",") if x.strip()]
    if name is not None:
        body["name"] = name
        body["setName"] = True
    if enabled is not None:
        body["enabled"] = enabled
    if not body:
        raise click.ClickException("无更新字段")
    client = make_client(config)
    try:
        data = asyncio.run(client.update_webhook(webhook_id, body))
        if json_mode:
            echo_json(True, data=data, message="updated")
            return
        obj.skin.success(f"已更新: {(data.get('id') or webhook_id)[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@webhook_cli.command(name="delete")
@click.argument("webhook_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_delete(obj, webhook_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.delete_webhook(webhook_id))
        if json_mode:
            echo_json(True, data=data, message="deleted")
            return
        obj.skin.success(f"已删除: {webhook_id[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@webhook_cli.command(name="test")
@click.argument("webhook_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def webhook_test(obj, webhook_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.test_webhook(webhook_id))
        if json_mode:
            echo_json(True, data=data, message="tested")
            return
        if (data or {}).get("success"):
            obj.skin.success(
                f"测试成功 HTTP {data.get('statusCode')} attempt={data.get('attempt')}"
            )
        else:
            obj.skin.error(f"测试失败: {data.get('error') or data}")
    except APIError as e:
        handle_api_error(e, json_mode)
