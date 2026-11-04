"""Recurring Issues commands (E35)."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config


@click.group(name="recurrence")
def recurrence_cli():
    """周期建单（Recurring Issues）。"""
    pass


@recurrence_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def recurrence_list(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_recurrences())
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("无周期规则")
            return
        obj.skin.table(
            ["Template", "Interval", "Next(UTC)", "Enabled", "LastIssue", "Id"],
            [
                [
                    (r.get("titleTemplate") or "")[:40],
                    r.get("interval") or "",
                    (r.get("nextRunAt") or "")[:19],
                    "yes" if r.get("enabled") else "no",
                    (r.get("lastIssueId") or "")[:8],
                    (r.get("id") or "")[:8],
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@recurrence_cli.command(name="create")
@click.option("--title-template", "-t", required=True, help="支持 {date}/{yyyy-mm-dd}")
@click.option("--interval", "-i", type=click.Choice(["daily", "weekly", "monthly"]), required=True)
@click.option("--next-run-at", required=True, help="ISO datetime UTC naive")
@click.option("--description", "-d", default=None)
@click.option("--priority", default=None)
@click.option("--label", multiple=True, help="可重复；tag name")
@click.option("--project-id", default=None)
@click.option("--assignee-id", default=None)
@click.option("--custom-fields-json", default=None, help='如 {"severity":"p0"}')
@click.option("--weekday", type=int, default=None, help="weekly: 0=Mon..6=Sun")
@click.option("--monthday", type=int, default=None, help="monthly: 1-31")
@click.option("--disabled", is_flag=True)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def recurrence_create(
    obj,
    title_template,
    interval,
    next_run_at,
    description,
    priority,
    label,
    project_id,
    assignee_id,
    custom_fields_json,
    weekday,
    monthday,
    disabled,
    as_json,
):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    body = {
        "titleTemplate": title_template,
        "interval": interval,
        "nextRunAt": next_run_at,
        "enabled": not disabled,
    }
    if description is not None:
        body["description"] = description
    if priority is not None:
        body["priority"] = priority
    if label:
        body["labels"] = list(label)
    if project_id is not None:
        body["projectId"] = project_id
    if assignee_id is not None:
        body["assigneeId"] = assignee_id
    if custom_fields_json:
        body["customFields"] = json.loads(custom_fields_json)
    if weekday is not None:
        body["weekday"] = weekday
    if monthday is not None:
        body["monthday"] = monthday
    client = make_client(config)
    try:
        data = asyncio.run(client.create_recurrence(body))
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        obj.skin.success(f"已创建: {(data.get('id') or '')[:8]} next={data.get('nextRunAt')}")
    except APIError as e:
        handle_api_error(e, json_mode)


@recurrence_cli.command(name="update")
@click.argument("recurrence_id")
@click.option("--title-template", default=None)
@click.option("--interval", type=click.Choice(["daily", "weekly", "monthly"]), default=None)
@click.option("--next-run-at", default=None)
@click.option("--description", default=None)
@click.option("--priority", default=None)
@click.option("--enabled", type=click.BOOL, default=None)
@click.option("--labels-json", default=None, help='JSON 数组覆盖 labels')
@click.option("--custom-fields-json", default=None)
@click.option("--weekday", type=int, default=None)
@click.option("--monthday", type=int, default=None)
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def recurrence_update(
    obj,
    recurrence_id,
    title_template,
    interval,
    next_run_at,
    description,
    priority,
    enabled,
    labels_json,
    custom_fields_json,
    weekday,
    monthday,
    as_json,
):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    body = {}
    if title_template is not None:
        body["titleTemplate"] = title_template
    if interval is not None:
        body["interval"] = interval
    if next_run_at is not None:
        body["nextRunAt"] = next_run_at
    if description is not None:
        body["description"] = description
    if priority is not None:
        body["priority"] = priority
        body["setPriority"] = True
    if enabled is not None:
        body["enabled"] = enabled
    if labels_json is not None:
        body["labels"] = json.loads(labels_json)
    if custom_fields_json is not None:
        body["customFields"] = json.loads(custom_fields_json)
    if weekday is not None:
        body["weekday"] = weekday
        body["setWeekday"] = True
    if monthday is not None:
        body["monthday"] = monthday
        body["setMonthday"] = True
    if not body:
        raise click.UsageError("请至少提供一个更新字段")
    client = make_client(config)
    try:
        data = asyncio.run(client.update_recurrence(recurrence_id, body))
        if json_mode:
            echo_json(True, data=data, message="updated")
            return
        obj.skin.success(f"已更新: {(data.get('id') or '')[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@recurrence_cli.command(name="delete")
@click.argument("recurrence_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def recurrence_delete(obj, recurrence_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.delete_recurrence(recurrence_id))
        if json_mode:
            echo_json(True, data=data, message="deleted")
            return
        obj.skin.success(f"已删除: {recurrence_id[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@recurrence_cli.command(name="run-due")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def recurrence_run_due(obj, as_json):
    """创建所有到期的周期 Issue，并推进 next_run_at（UTC）。"""
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.run_due_recurrences())
        if json_mode:
            echo_json(True, data=data, message="run-due")
            return
        created = (data or {}).get("created", 0)
        errors = (data or {}).get("errors") or []
        obj.skin.success(f"created={created} errors={len(errors)}")
        for iss in (data or {}).get("issues") or []:
            obj.skin.info(f"  {iss.get('issueCode')} {iss.get('title')}")
    except APIError as e:
        handle_api_error(e, json_mode)
