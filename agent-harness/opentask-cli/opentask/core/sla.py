"""SLA policy + clocks + run-due commands (E42)."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="sla")
def sla_cli():
    """SLA 策略 / Issue 时钟 / run-due tick。"""
    pass


@sla_cli.group(name="policy")
def policy_cli():
    """SLA 策略 CRUD。"""
    pass


@policy_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def policy_list(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_sla_policies())
        rows = (data or {}).get("rows") or []
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.section(f"SLA policies ({len(rows)})")
        table = []
        for r in rows:
            table.append(
                [
                    (r.get("id") or "")[:8],
                    r.get("name") or "",
                    "on" if r.get("enabled") else "off",
                    str(r.get("targetMinutes") or ""),
                    ",".join(r.get("startStatuses") or []),
                ]
            )
        obj.skin.table(["ID", "Name", "Enabled", "Minutes", "Start"], table)
    except APIError as e:
        handle_api_error(e, json_mode)


@policy_cli.command(name="show")
@click.argument("policy_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def policy_show(obj, policy_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_sla_policies())
        rows = (data or {}).get("rows") or []
        row = next((r for r in rows if r.get("id") == policy_id or (r.get("id") or "").startswith(policy_id)), None)
        if not row:
            raise click.ClickException("策略不存在")
        if json_mode:
            echo_json(True, data=row)
            return
        obj.skin.section(row.get("name") or policy_id)
        for k, v in row.items():
            obj.skin.info(f"{k}: {v}")
    except APIError as e:
        handle_api_error(e, json_mode)


@policy_cli.command(name="create")
@click.option("--name", required=True)
@click.option("--start", "starts", multiple=True, required=True, help="start status (repeatable)")
@click.option("--stop", "stops", multiple=True, help="stop status (repeatable; empty=closed-class)")
@click.option("--minutes", default=1440, show_default=True, type=int)
@click.option("--notify-assignee/--no-notify-assignee", default=True)
@click.option("--notify-watchers/--no-notify-watchers", default=False)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def policy_create(obj, name, starts, stops, minutes, notify_assignee, notify_watchers, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    body = {
        "name": name,
        "startStatuses": list(starts),
        "stopStatuses": list(stops),
        "targetMinutes": minutes,
        "notifyAssignee": notify_assignee,
        "notifyWatchers": notify_watchers,
    }
    client = make_client(config)
    try:
        data = asyncio.run(client.create_sla_policy(body))
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        obj.skin.success(f"已创建: {(data or {}).get('id', '')[:8]} {name}")
    except APIError as e:
        handle_api_error(e, json_mode)


@policy_cli.command(name="update")
@click.argument("policy_id")
@click.option("--name", default=None)
@click.option("--minutes", default=None, type=int)
@click.option("--enabled/--disabled", "enabled", default=None)
@click.option("--json-body", default=None, help="raw JSON patch body")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def policy_update(obj, policy_id, name, minutes, enabled, json_body, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    body = {}
    if json_body:
        try:
            body = json.loads(json_body)
        except json.JSONDecodeError as e:
            raise click.ClickException(f"无效 JSON: {e}") from e
    if name is not None:
        body["name"] = name
    if minutes is not None:
        body["targetMinutes"] = minutes
    if enabled is not None:
        body["enabled"] = enabled
    if not body:
        raise click.ClickException("无更新字段")
    client = make_client(config)
    try:
        data = asyncio.run(client.update_sla_policy(policy_id, body))
        if json_mode:
            echo_json(True, data=data, message="updated")
            return
        obj.skin.success(f"已更新: {policy_id[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@policy_cli.command(name="delete")
@click.argument("policy_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def policy_delete(obj, policy_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.delete_sla_policy(policy_id))
        if json_mode:
            echo_json(True, data=data, message="deleted")
            return
        obj.skin.success(f"已删除: {policy_id[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@sla_cli.command(name="issue")
@click.argument("issue_ref")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def sla_issue(obj, issue_ref, as_json):
    """列出 Issue 的 SLA 时钟（id 或 issue code）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.get_issue_sla(issue_ref))
        rows = (data or {}).get("rows") or []
        if json_mode:
            echo_json(True, data=data)
            return
        obj.skin.section(f"SLA clocks for {issue_ref} ({len(rows)})")
        table = []
        for r in rows:
            table.append(
                [
                    (r.get("id") or "")[:8],
                    r.get("policyName") or (r.get("policyId") or "")[:8],
                    r.get("status"),
                    (r.get("deadlineAt") or "")[:19],
                ]
            )
        obj.skin.table(["Clock", "Policy", "Status", "Deadline"], table)
    except APIError as e:
        handle_api_error(e, json_mode)


@sla_cli.command(name="run-due")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def sla_run_due(obj, as_json):
    """将到期 running 时钟标为 breached 并投递 Inbox（UTC；无内置 cron）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.run_due_sla())
        if json_mode:
            echo_json(True, data=data, message="run-due")
            return
        obj.skin.success(
            f"scanned={data.get('scanned')} breached={data.get('breached')} "
            f"notifications={data.get('notificationsCreated')} skipped={data.get('skipped')}"
        )
        for err in data.get("errors") or []:
            obj.skin.warn(f"  error {err.get('clockId')}: {err.get('message')}")
    except APIError as e:
        handle_api_error(e, json_mode)
