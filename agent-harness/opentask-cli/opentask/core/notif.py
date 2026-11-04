"""Notification preference + email + due-reminders commands (E27/E30/E39)."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config

PREF_KEYS = [
    "issue_assigned",
    "issue_comment",
    "issue_mention",
    "issue_status",
    "due_date_changed",
    "issue_watch_event",
    "automation_comment",
    "due_reminder",
    "due_reminder_digest",
    "email_enabled",
]


@click.group(name="notif")
def notif_cli():
    """通知相关（偏好 / 邮件测试 / 到期提醒 tick）。"""
    pass


@notif_cli.group(name="prefs")
def prefs_cli():
    """通知偏好（当前 workspace）。"""
    pass


@prefs_cli.command(name="get")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def prefs_get(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_notif_prefs())
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.section("Notification preferences")
        rows = []
        for k in PREF_KEYS:
            val = (data or {}).get(k)
            rows.append([k, "on" if val else "off"])
        configured = (data or {}).get("email_configured")
        rows.append(["email_configured", "yes" if configured else "no"])
        obj.skin.table(["Key", "Enabled"], rows)
    except APIError as e:
        handle_api_error(e, json_mode)


@prefs_cli.command(name="set")
@click.option("--key", "pref_key", default=None, type=click.Choice(PREF_KEYS, case_sensitive=False))
@click.option("--on", "turn_on", is_flag=True, help="启用该 key")
@click.option("--off", "turn_off", is_flag=True, help="关闭该 key")
@click.option("--json-body", "json_body", default=None, help='JSON 对象，如 {"issue_comment":false}')
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def prefs_set(obj, pref_key, turn_on, turn_off, json_body, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)

    updates = {}
    if json_body:
        try:
            parsed = json.loads(json_body)
        except json.JSONDecodeError as e:
            raise click.ClickException(f"无效 JSON: {e}") from e
        if not isinstance(parsed, dict):
            raise click.ClickException("JSON 必须是对象")
        for k, v in parsed.items():
            if k not in PREF_KEYS:
                raise click.ClickException(f"未知偏好键: {k}")
            updates[k] = bool(v)
    elif pref_key:
        if turn_on == turn_off:
            raise click.ClickException("请指定 --on 或 --off（互斥）")
        updates[pref_key] = bool(turn_on)
    else:
        raise click.ClickException("请提供 --key/--on|--off 或 --json-body")

    client = make_client(config)
    try:
        data = asyncio.run(client.put_notif_prefs(updates))
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success("已保存")
        for k, v in updates.items():
            obj.skin.info(f"{k} = {'on' if (data or {}).get(k, v) else 'off'}")
    except APIError as e:
        handle_api_error(e, json_mode)


@notif_cli.command(name="email-test")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def email_test(obj, as_json):
    """向当前用户发送一封测试邮件（需 SMTP 已配置）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.notif_email_test())
        if json_mode:
            echo_json(True, data=data)
            return
        to = (data or {}).get("to") or ""
        obj.skin.success(f"测试邮件已发送 → {to}" if to else "测试邮件已发送")
    except APIError as e:
        handle_api_error(e, json_mode)


@notif_cli.command(name="run-due-reminders")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def run_due_reminders(obj, as_json):
    """执行到期提醒 tick（UTC；外部调度，无内置 cron）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.run_due_reminders())
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.success("已执行 due reminders")
        if isinstance(data, dict):
            obj.skin.info(
                f"processed={data.get('processedIssues')} "
                f"reminders={data.get('remindersCreated')} "
                f"digests={data.get('digestsCreated')} "
                f"skipped={data.get('skipped')}"
            )
    except APIError as e:
        handle_api_error(e, json_mode)


@notif_cli.command(name="due-deliveries")
@click.option("--bucket-date", "bucket_date", default=None, help="UTC YYYY-MM-DD")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def due_deliveries(obj, bucket_date, as_json):
    """列出到期提醒投递账本（只读）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_due_reminder_deliveries(bucket_date=bucket_date))
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows") or []
        obj.skin.section(f"Due reminder deliveries ({len(rows)})")
        table = []
        for r in rows:
            table.append(
                [
                    r.get("kind"),
                    r.get("userId"),
                    r.get("issueId") or "-",
                    r.get("bucketDate"),
                    r.get("dueDateBucket") or "-",
                ]
            )
        obj.skin.table(["Kind", "User", "Issue", "Bucket", "DueBucket"], table)
    except APIError as e:
        handle_api_error(e, json_mode)
