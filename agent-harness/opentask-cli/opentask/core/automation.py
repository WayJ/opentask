"""Automation commands (E26)."""
from __future__ import annotations

import asyncio
import json

import click

from ..utils.api_client import APIError
from ..utils.cli_output import echo_json, handle_api_error, make_client, require_workspace_id
from ..utils.config import Config

TRIGGERS = [
    "issue.created",
    "issue.status_changed",
    "issue.assignee_changed",
    "label_added",
]
ACTIONS = [
    "set_status",
    "set_assignee",
    "add_label",
    "set_priority",
    "add_comment",
]


@click.group(name="automation")
def automation_cli():
    """Workspace 自动化规则。"""
    pass


@automation_cli.command(name="list")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def automation_list(obj, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.list_automations())
        if json_mode:
            echo_json(True, data=data)
            return
        rows = (data or {}).get("rows", []) if isinstance(data, dict) else []
        if not rows:
            obj.skin.info("无自动化规则")
            return
        obj.skin.table(
            ["Name", "Trigger", "Action", "Enabled", "Id"],
            [
                [
                    r.get("name") or "",
                    r.get("triggerType") or "",
                    r.get("actionType") or "",
                    "yes" if r.get("enabled") else "no",
                    (r.get("id") or "")[:8],
                ]
                for r in rows
            ],
        )
    except APIError as e:
        handle_api_error(e, json_mode)


@automation_cli.command(name="create")
@click.option("--name", "-n", required=True)
@click.option("--trigger", "trigger_type", required=True, type=click.Choice(TRIGGERS, case_sensitive=False))
@click.option("--action", "action_type", required=True, type=click.Choice(ACTIONS, case_sensitive=False))
@click.option("--trigger-config", default="{}", help="JSON object")
@click.option("--action-config", default="{}", help="JSON object")
@click.option("--condition", default=None, help="JSON object；省略=无条件")
@click.option("--disabled", is_flag=True, help="创建为禁用")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def automation_create(
    obj, name, trigger_type, action_type, trigger_config, action_config, condition, disabled, as_json
):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    try:
        tcfg = json.loads(trigger_config or "{}")
        acfg = json.loads(action_config or "{}")
        cond = json.loads(condition) if condition else None
    except json.JSONDecodeError as e:
        raise click.ClickException(f"JSON 无效: {e}") from e
    client = make_client(config)
    try:
        data = asyncio.run(
            client.create_automation(
                name,
                trigger_type,
                action_type,
                trigger_config=tcfg,
                action_config=acfg,
                condition=cond,
                enabled=not disabled,
            )
        )
        if json_mode:
            echo_json(True, data=data, message="created")
            return
        obj.skin.success(f"已创建规则: {data.get('name')} ({(data.get('id') or '')[:8]})")
    except APIError as e:
        handle_api_error(e, json_mode)


@automation_cli.command(name="enable")
@click.argument("rule_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def automation_enable(obj, rule_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.enable_automation(rule_id))
        if json_mode:
            echo_json(True, data=data, message="enabled")
            return
        obj.skin.success(f"已启用: {(data.get('id') or rule_id)[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)


@automation_cli.command(name="disable")
@click.argument("rule_id")
@click.option("--json", "as_json", is_flag=True)
@click.pass_obj
def automation_disable(obj, rule_id, as_json):
    config: Config = obj.config
    json_mode = as_json or obj.json_mode
    if not require_workspace_id(config, json_mode):
        raise SystemExit(1)
    client = make_client(config)
    try:
        data = asyncio.run(client.disable_automation(rule_id))
        if json_mode:
            echo_json(True, data=data, message="disabled")
            return
        obj.skin.success(f"已禁用: {(data.get('id') or rule_id)[:8]}")
    except APIError as e:
        handle_api_error(e, json_mode)
